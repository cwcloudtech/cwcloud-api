import os
import importlib
import requests
import pulumi
import pulumiverse_scaleway as scaleway

from pulumi import ResourceOptions
from pulumi import automation as auto
from urllib.error import HTTPError

from drivers.ProviderDriver import ProviderDriver
from utils.common import is_not_empty, is_true
from utils.dns_zones import get_dns_zone_driver, register_scaleway_domain
from utils.driver import convert_instance_state, sanitize_project_name
from utils.dynamic_name import rehash_dynamic_name
from utils.http import HTTP_REQUEST_TIMEOUT
from utils.list import unmarshall_list_array
from utils.logger import log_msg

SCW_API_URL = "https://api.scaleway.com"
SCW_ACCESS_KEY = os.getenv('SCW_ACCESS_KEY')
SCW_SECRET_KEY = os.getenv('SCW_SECRET_KEY')
SCW_PROJECT_ID = os.getenv('SCW_PROJECT_ID')

class ScalewayDriver(ProviderDriver):
    def create_dns_records(self, record_name, environment, ip_address, root_dns_zone):
        dnsZonesResponse = requests.get(f'{SCW_API_URL}/domain/v2beta1/domains/{root_dns_zone}/dns-zones', headers={"X-Auth-Token": SCW_SECRET_KEY}, timeout=HTTP_REQUEST_TIMEOUT)
        dnsZones = dnsZonesResponse.json()["dns_zones"]
        availableZones = []
        for zone in dnsZones:
            availableZones.append(zone['subdomain'])

        if not environment['path'] in availableZones:
            newDnsInfo = {
                "domain": root_dns_zone,
                "subdomain": environment['path'],
                "project_id": SCW_PROJECT_ID
            }
            dnsZones = requests.post(f'{SCW_API_URL}/domain/v2beta1/dns-zones', headers={"X-Auth-Token": SCW_SECRET_KEY}, json=newDnsInfo, timeout=HTTP_REQUEST_TIMEOUT)

        register_scaleway_domain(record_name, environment['path'], ip_address, root_dns_zone)
        for subdomain in unmarshall_list_array(environment['subdomains']):
            dns_record_name = "{}.{}".format(subdomain, record_name)
            register_scaleway_domain(dns_record_name, environment['path'], ip_address, root_dns_zone)
            
    def create_custom_dns_record(self, record_name, dns_zone, record_type, ttl, data):
        def create_pulumi_program():
            json = {
                "changes": [{
                    "add": {
                        "records": [
                            {
                                "name": record_name,
                                "ttl": ttl,
                                "type": record_type,
                                "data": data,
                                "priority": 0,
                            }
                        ]
                    }
                }]
            }
            requests.patch(f'{SCW_API_URL}/domain/v2beta1/dns-zones/{dns_zone}/records', headers={"X-Auth-Token": SCW_SECRET_KEY}, json=json, timeout=HTTP_REQUEST_TIMEOUT)
            
            pulumi.export("record", record_name)
            pulumi.export("zone", dns_zone)
            pulumi.export("type", record_type)
            pulumi.export("ttl", ttl)
            pulumi.export("data", data)
        
        stack = auto.create_or_select_stack(stack_name = "scw-create-{}-{}".format(record_name, dns_zone),
                                            project_name = "dns-records",
                                            program = create_pulumi_program)
        stack.up()
        return {"record": record_name, "zone": dns_zone, "type": record_type, "ttl": ttl, "data": data}
        
    def list_dns_records(self):
        dnsZonesResponse = requests.get(f'{SCW_API_URL}/domain/v2beta1/domains', headers={"X-Auth-Token": SCW_SECRET_KEY}, timeout=HTTP_REQUEST_TIMEOUT)
        dnsZones = dnsZonesResponse.json()["domains"]
        allRecords = []
        for zone in dnsZones:
            zoneName = zone['domain']
            zoneRecordsResponse = requests.get(f'{SCW_API_URL}/domain/v2beta1/dns-zones/{zoneName}/records', headers={"X-Auth-Token": SCW_SECRET_KEY}, timeout=HTTP_REQUEST_TIMEOUT)
            zoneRecords = zoneRecordsResponse.json()["records"]
            for record in zoneRecords:
                allRecords.append({
                    "id": record['id'],
                    "zone": zoneName,
                    "record": record['name'],
                    "ttl": record['ttl'],
                    "type": record['type'],
                    "data": record['data']
                })
        return allRecords
    
    def delete_dns_records(self, id, record_name, root_dns_zone):
        def create_pulumi_program():
            data = {
                "changes": [{
                    "delete": {
                        "id": id
                        }
                    }]
                }
            requests.patch(f'{SCW_API_URL}/domain/v2beta1/dns-zones/{root_dns_zone}/records', headers={"X-Auth-Token": SCW_SECRET_KEY}, json=data, timeout=HTTP_REQUEST_TIMEOUT)
        stack = auto.create_or_select_stack(stack_name = "{}-{}".format(id, record_name),
                                            project_name = "dns-records",
                                            program = create_pulumi_program)
        stack.up()
        return {"id": id, "record": record_name, "zone": root_dns_zone}
         
    def create_instance(self, hashed_instance_name, environment, instance_region, instance_zone, instance_type, ami_image, generate_dns, root_dns_zone):
        def create_pulumi_program():
            region_zone = "{}-{}".format(instance_region, instance_zone)
            instance_ip = scaleway.InstanceIp("publicIp", zone = region_zone)
            scaleway.InstanceServer(hashed_instance_name,
                type = instance_type,
                image = ami_image,
                name = hashed_instance_name,
                ip_id = instance_ip.id,
                zone = region_zone,
                user_data = {
                    "cloud-init": (lambda path: open(path).read())(self.cloud_init_script())
                }
            )

            if is_true(generate_dns):
                dns_driver = get_dns_zone_driver(root_dns_zone)
                ProviderDriverModule = importlib.import_module('drivers.{}'.format(dns_driver))
                ProviderDriver = getattr(ProviderDriverModule, dns_driver)
                ProviderDriver().create_dns_records(hashed_instance_name, environment, instance_ip.address, root_dns_zone)
            pulumi.export("public_ip", instance_ip.address)

        cloudflare_api_token = os.getenv('CLOUDFLARE_API_TOKEN')

        stack = auto.create_or_select_stack(stack_name = hashed_instance_name,
                                            project_name = sanitize_project_name(environment['path']),
                                            program = create_pulumi_program)
        stack.set_config("scaleway:accessKey", auto.ConfigValue(SCW_ACCESS_KEY))
        stack.set_config("scaleway:secretKey", auto.ConfigValue(SCW_SECRET_KEY))
        stack.set_config("scaleway:projectId", auto.ConfigValue(SCW_PROJECT_ID))
        if is_not_empty(cloudflare_api_token):
            stack.set_config("cloudflare:api_token", auto.ConfigValue(cloudflare_api_token))
        up_res = stack.up()

        return {
            "ip": up_res.outputs.get("public_ip").value
        }

    def refresh_instance(self, hashed_instance_name, environment, instance_region, instance_zone):
        def create_pulumi_program():
            region_zone = "{}-{}".format(instance_region, instance_zone)
            existing_instance = scaleway.get_instance_server(hashed_instance_name)
            existingInstanceIp = scaleway.get_instance_ip(existing_instance.public_ip)
            scaleway.InstanceIp("publicIp", opts = ResourceOptions(import_ = existingInstanceIp.id))
            scaleway.InstanceServer(hashed_instance_name,
                                    image = existing_instance.image,
                                    name = hashed_instance_name,
                                    type = existing_instance.type,
                                    zone = region_zone,
                                    ip_id = existing_instance.ip_id,
                                    enable_ipv6 = True,
                                    state = existing_instance.state,
                                    user_data = existing_instance.user_data,
                                    opts = ResourceOptions(import_ = existing_instance.id))
            pulumi.export("ip_address", existing_instance.public_ip)
            pulumi.export("type", existing_instance.type)
 

        stack = auto.create_or_select_stack(stack_name = hashed_instance_name,
                                            project_name = sanitize_project_name(environment['path']),
                                            program = create_pulumi_program)

        stack.set_config("scaleway:accessKey", auto.ConfigValue(SCW_ACCESS_KEY))
        stack.set_config("scaleway:secretKey", auto.ConfigValue(SCW_SECRET_KEY))
        stack.set_config("scaleway:projectId", auto.ConfigValue(SCW_PROJECT_ID))
        log_msg("DEBUG", "[ScalewayDriver] Refreshing instance {}".format(hashed_instance_name))
        up_res = stack.up()

        return {
            "type": up_res.outputs.get("ip_address").value,
            "ip": up_res.outputs.get("type").value
        }

    def refresh_registry(self, user_email, hashed_registry_name):
        def create_pulumi_program():
            existing_registry = scaleway.get_registry_namespace(name = hashed_registry_name, opts = None)
            pulumi.export("type", existing_registry.type)

        try:
            stack = auto.create_or_select_stack(stack_name = hashed_registry_name,
                                                project_name = sanitize_project_name(user_email),
                                                program = create_pulumi_program)

            stack.set_config("scaleway:accessKey", auto.ConfigValue(SCW_ACCESS_KEY))
            stack.set_config("scaleway:secretKey", auto.ConfigValue(SCW_SECRET_KEY))
            log_msg("DEBUG", "[ScalewayDriver] Refreshing registry {}".format(hashed_registry_name))
            up_res = stack.up()
            return {
                "type": up_res.outputs.get("type").value
            }
        except Exception as e:
            log_msg("WARN", "[Scaleway][refresh_bucket] unexpected error: {}".format(e))
            return {
                "error": "{}".format(e)
            }

    def refresh_bucket(self, user_email, hashed_bucket_name):
        def create_pulumi_program():
            existing_bucket = scaleway.get_object_bucket(name = hashed_bucket_name)
            pulumi.export("type", existing_bucket.type)

        try:
            stack = auto.create_or_select_stack(stack_name = hashed_bucket_name,
                                                project_name = sanitize_project_name(user_email),
                                                program = create_pulumi_program)

            stack.set_config("scaleway:accessKey", auto.ConfigValue(SCW_ACCESS_KEY))
            stack.set_config("scaleway:secretKey", auto.ConfigValue(SCW_SECRET_KEY))
            log_msg("DEBUG", "[ScalewayDriver] Refreshing bucket {}".format(hashed_bucket_name))
            up_res = stack.up()
            return {
                "type": up_res.outputs.get("type").value
            }
        except Exception as e:
            log_msg("WARN", "[Scaleway][refresh_bucket] unexpected error: {}".format(e))
            return {
                "error": "{}".format(e)
            }

    def get_server_state(self, server):
        switcher = {
          "stopped": "stopped",
          "rebooting": "rebooting",
          "starting": "starting",
          "stopping": "stopping",
          "running": "running"
        }

        return convert_instance_state(switcher, server)

    def get_virtual_machine(self, region, zone, instance_name):
        region_zone = "{}-{}".format(region, zone)
        sw_api_key = os.getenv('SCW_SECRET_KEY')
        res = requests.get(f'{SCW_API_URL}/instance/v1/zones/{region_zone}/servers?name={instance_name}', headers={"X-Auth-Token": sw_api_key}, timeout=HTTP_REQUEST_TIMEOUT)
        servers = res.json()['servers']
        if len(servers)>0:
            return servers[0]
        return None

    def update_virtual_machine_status(self, region, zone, server_id, action):
        regionZone = "{}-{}".format(region, zone)
        actionData = {'action':action}
        res = requests.post(f'{SCW_API_URL}/instance/v1/zones/{regionZone}/servers/{server_id}/action',
                                headers={"X-Auth-Token": SCW_SECRET_KEY},
                                json=actionData,
                                timeout=HTTP_REQUEST_TIMEOUT
                            )
        if res.status_code == 404:
            message = f"resource {server_id} not found."
            raise HTTPError("instance_not_found", res.status_code, message, hdrs = {"i18n_code": "instance_not_found"}, fp = None)

    def create_bucket(self, user_email, hashed_bucket_name, region, bucket_type):
        def create_pulumi_program():
            object_storage = scaleway.ObjectBucket(resource_name = hashed_bucket_name,
                                                acl = bucket_type,
                                                name = hashed_bucket_name,
                                                region = region)
            pulumi.export("endpoint", object_storage.endpoint)
        stack = auto.create_or_select_stack(stack_name = hashed_bucket_name,
                                            project_name = sanitize_project_name(user_email),
                                            program = create_pulumi_program)
        stack.set_config("scaleway:accessKey", auto.ConfigValue(SCW_ACCESS_KEY))
        stack.set_config("scaleway:secretKey", auto.ConfigValue(SCW_SECRET_KEY))
        stack.set_config("scaleway:projectId", auto.ConfigValue(SCW_PROJECT_ID))
        up_res = stack.up()

        return {
            "endpoint": up_res.outputs.get("endpoint").value,
            "access_key": None,
            "secret_key": None,
            "status": "active"
        }

    def update_bucket_credentials(self, bucket):
        return {
            "access_key": None,
            "secret_key": None
        }

    def delete_bucket(self, bucket, user_email):
        hashed_bucket_name = rehash_dynamic_name(bucket.name, bucket.hash)
        stack = auto.select_stack(hashed_bucket_name, sanitize_project_name(user_email), program = self.delete_bucket)
        stack.destroy()

    def create_registry(self, user_email, hashed_name, region, type):
        def create_pulumi_program():
            isPublic = True
            if type == 'private':
                isPublic = False
            registry = scaleway.RegistryNamespace(hashed_name, name = hashed_name, region = region, is_public = isPublic)
            pulumi.export("endpoint", registry.endpoint)
        stack = auto.create_or_select_stack(stack_name = hashed_name,
                                            project_name = sanitize_project_name(user_email),
                                            program = create_pulumi_program)
        stack.set_config("scaleway:accessKey", auto.ConfigValue(SCW_ACCESS_KEY))
        stack.set_config("scaleway:secretKey", auto.ConfigValue(SCW_SECRET_KEY))
        stack.set_config("scaleway:projectId", auto.ConfigValue(SCW_PROJECT_ID))
        up_res = stack.up()

        return {
            "endpoint": up_res.outputs.get("endpoint").value,
            "access_key": None,
            "secret_key": None,
            "status": "active"
        }

    def update_registry_credentials(self, registry):
        return {
            "access_key": None,
            "secret_key": None
        }

    def delete_registry(self, registry, user_email):
        hashed_name = rehash_dynamic_name(registry.name, registry.hash)
        stack = auto.select_stack(hashed_name, sanitize_project_name(user_email), program = self.delete_bucket)
        stack.destroy()

    def cloud_init_script(self):
        return "cloud-init.yml"
