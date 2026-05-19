import os
import importlib
import pulumi
import pulumi_ovh as ovh

from pulumi_openstack import compute
from openstack import connection
from pulumi import automation as auto, ResourceOptions
from pulumi_openstack.compute import _inputs

from drivers.ProviderDriver import ProviderDriver
from utils.common import is_not_empty
from utils.dns_zones import get_dns_zone_driver, register_ovh_domain
from utils.driver import sanitize_project_name
from utils.dynamic_name import rehash_dynamic_name
from utils.logger import log_msg
from utils.ovh_client import create_custom_dns_record, create_ovh_bucket, delete_ovh_bucket, delete_ovh_dns_record, list_ovh_dns_records, update_ovh_bucket_credentials, update_ovh_registry_credentials, ovh_client
from utils.list import unmarshall_list_array

def get_openstack_connection(region):
    os_auth_url = os.getenv('OS_AUTH_URL')
    os_username = os.getenv('OS_USERNAME')
    os_password = os.getenv('OS_PASSWORD')
    os_project_name = os.getenv('OS_TENANT_NAME')
    os_domain_name = os.getenv('OS_DOMAIN_NAME')

    con = connection.Connection(
        region_name = region,
        auth = dict(
            auth_url = os_auth_url,
            username = os_username,
            password = os_password,
            project_name = os_project_name,
            domain_name = os_domain_name),
        compute_api_version = '2')
    return con

class OvhDriver(ProviderDriver):
    def create_dns_records(self, record_name, environment, ip_address, root_dns_zone):
        register_ovh_domain(record_name, environment['path'], ip_address, root_dns_zone)
        for subdomain in unmarshall_list_array(environment['subdomains']):
            dns_record_name = "{}.{}".format(subdomain, record_name)
            register_ovh_domain(dns_record_name, environment['path'], ip_address, root_dns_zone)

    def refresh_instance(self, hashed_instance_name, environment, instance_region, instance_zone):
        target_vm = self.get_virtual_machine(instance_region, instance_zone, hashed_instance_name)
        log_msg("DEBUG", "[refresh_instance] target_vm[id] = {}".format(target_vm["id"]))
        def create_pulumi_program():
            new_instance = compute.Instance(hashed_instance_name,
                                    name = hashed_instance_name,
                                    opts = ResourceOptions(import_ = target_vm["id"]))
            pulumi.export("ip_address", new_instance.access_ip_v4)
            pulumi.export("type", new_instance.flavor_name)

        stack = auto.create_or_select_stack(stack_name = hashed_instance_name,
                                            project_name = sanitize_project_name(environment['path']),
                                            program = create_pulumi_program)

        up_res = stack.up()
        return {
            "ip": up_res.outputs.get("ip_address").value,
            "type": up_res.outputs.get("type").value
        }

    def refresh_registry(self, user_email, hashed_registry_name):
        def create_pulumi_program():
            registry = compute.get_flavor(name = hashed_registry_name)
            pulumi.export("type", registry.flavor_name)

        stack = auto.create_or_select_stack(stack_name = hashed_registry_name,
                                            project_name = sanitize_project_name(user_email),
                                            program = create_pulumi_program)

        up_res = stack.up()

        new_type = up_res.outputs.get("type").value
        return {
            "type": new_type
        }

    def refresh_bucket(self, user_email, hashed_bucket_name):
        return {}

    def create_instance(self, hashed_instance_name, environment, instance_region, instance_zone, instance_type, ami_image, generate_dns, root_dns_zone):
        def create_pulumi_program():
            con = get_openstack_connection(instance_region)
            ext_network = con.network.find_network("Ext-Net")
            new_instance = compute.Instance(hashed_instance_name,
                region = instance_region,
                availability_zone = instance_zone,
                flavor_name = instance_type,
                image_id = ami_image,
                name = hashed_instance_name,
                networks = [ _inputs.InstanceNetworkArgs(name = ext_network["name"], uuid = ext_network["id"])],
                user_data = (lambda path: open(path).read())(self.cloud_init_script())
            )

            if generate_dns == "true":
                dns_driver = get_dns_zone_driver(root_dns_zone)
                ProviderDriverModule = importlib.import_module('drivers.{}'.format(dns_driver))
                ProviderDriver = getattr(ProviderDriverModule, dns_driver)
                ProviderDriver().create_dns_records(hashed_instance_name, environment, new_instance.access_ip_v4, root_dns_zone)

            pulumi.export("public_ip", new_instance.access_ip_v4)

        stack = auto.create_or_select_stack(stack_name = hashed_instance_name,
                                            project_name = sanitize_project_name(environment['path']),
                                            program = create_pulumi_program)
        cloudflare_api_token = os.getenv('CLOUDFLARE_API_TOKEN')
        if is_not_empty(cloudflare_api_token):
            stack.set_config("cloudflare:api_token", auto.ConfigValue(cloudflare_api_token))

        up_res = stack.up()
        return {
            "ip": up_res.outputs.get("public_ip").value
        }

    def get_server_state(self, server):
        switcher = {
            "SHUTOFF": "stopped",
            "HARD_REBOOT": "rebooting",
            "ACTIVE": "running"
        }
        return switcher.get(server['status'])

    def get_virtual_machine(self, region, zone, instance_name):
        con = get_openstack_connection(region)
        server = con.compute.find_server(instance_name)
        if not server:
            return None
        server_res = con.compute.get_server(server)
        return server_res

    def update_virtual_machine_status(self, region, zone, server_id, action):
        con = get_openstack_connection(region)
        log_msg("INFO", f"[OvhDriver][update_virtual_machine_status] Updating instance {server_id} status with action {action}")
        if action == "poweroff":
            con.compute.stop_server(server_id)
        elif action == "reboot":
            con.compute.reboot_server(server_id, "HARD")
        elif action == "poweron":
            con.compute.start_server(server_id)

    def create_bucket(self, user_email, hashed_bucket_name, region, bucket_type):
        mainRegion = ''.join([i for i in region if not i.isdigit()])
        service_name = os.getenv('OVH_SERVICENAME')
        def create_pulumi_program():
            user = ovh.cloudproject.User(hashed_bucket_name, service_name = service_name, description = hashed_bucket_name, role_name = "objectstore_operator")
            pulumi.export("user_id", user.id)

        stack = auto.create_or_select_stack(stack_name = hashed_bucket_name,
                                            project_name = sanitize_project_name(user_email),
                                            program = create_pulumi_program)
        up_res = stack.up()
        bucket_user_id = up_res.outputs.get("user_id").value
        (endpoint, access_key, secret_key) = create_ovh_bucket(hashed_bucket_name, mainRegion, bucket_user_id)

        return {
            "endpoint": endpoint,
            "user_id": bucket_user_id,
            "access_key": access_key,
            "secret_key": secret_key,
            "status": "active"
        }

    def update_bucket_credentials(self, bucket):
        credentials = update_ovh_bucket_credentials(bucket.bucket_user_id)
        return {
            "access_key": credentials["access_key"],
            "secret_key": credentials["secret_key"]
        }

    def delete_bucket(self, bucket, user_email):
        hashed_bucket_name = rehash_dynamic_name(bucket.name, bucket.hash)
        stack = auto.select_stack(hashed_bucket_name, sanitize_project_name(user_email), program = self.delete_bucket)
        stack.destroy()
        mainRegion = ''.join([i for i in bucket.region if not i.isdigit()])
        delete_ovh_bucket(hashed_bucket_name, mainRegion.upper(), bucket.bucket_user_id)

    def create_registry(self, user_email, hashed_name, region, type):
        mainRegion = ''.join([i for i in region if not i.isdigit()])
        service_name = os.getenv('OVH_SERVICENAME')
        def create_pulumi_program():
                reg = ovh.CloudProjectContainerRegistry(hashed_name,
                    name = hashed_name,
                    service_name = service_name,
                    region = mainRegion)
                pulumi.export("endpoint", reg.url)
        stack = auto.create_or_select_stack(stack_name = hashed_name,
                                            project_name = sanitize_project_name(user_email),
                                            program = create_pulumi_program)
        up_res = stack.up()
        credentials = update_ovh_registry_credentials(hashed_name)

        return {
            "endpoint": up_res.outputs.get("endpoint").value,
            "access_key": credentials["login"],
            "secret_key": credentials["password"],
            "status": "active"
        }

    def update_registry_credentials(self, registry):
        hashed_name = rehash_dynamic_name(registry.name, registry.hash)
        credentials = update_ovh_registry_credentials(hashed_name)
        return {
            "access_key": credentials["login"],
            "secret_key": credentials["password"]
        }

    def delete_registry(self, registry, user_email):
        hashed_name = rehash_dynamic_name(registry.name, registry.hash)
        stack = auto.select_stack(hashed_name, sanitize_project_name(user_email), program = self.delete_registry)
        stack.destroy()
        return

    def cloud_init_script(self):
        return "cloud-init.yml"
    
    def create_custom_dns_record(self, record_name, dns_zone, record_type, ttl, data):
        def create_pulumi_program():
            create_custom_dns_record(record_name, dns_zone, record_type, ttl, data)
        
        stack = auto.create_or_select_stack(stack_name = "ovh-create{}-{}".format(record_name, dns_zone),
                                            project_name = "dns-records",
                                            program = create_pulumi_program)
        stack.up()
        return {"record": record_name, "zone": dns_zone, "type": record_type, "ttl": ttl, "data": data}
    
    def delete_dns_records(self, id, record_name, root_dns_zone):
        def create_pulumi_program():
            delete_ovh_dns_record(id, root_dns_zone)
        stack = auto.create_or_select_stack(stack_name = "ovh-delete{}-{}".format(id, record_name),
                                            project_name = "dns-records",
                                            program = create_pulumi_program)
        stack.up()
        return  {"id": id, "record": record_name, "zone": root_dns_zone}
    
    def list_dns_records(self):
        return list_ovh_dns_records()
