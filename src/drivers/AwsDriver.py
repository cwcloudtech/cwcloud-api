import os
import importlib
import boto3
import pulumi
import pulumi_aws as aws

from pulumi import automation as auto
from botocore.config import Config

from drivers.ProviderDriver import ProviderDriver

from adapters.AdapterConfig import get_adapter
from utils.common import is_not_empty, is_true
from utils.dns_zones import get_dns_zone_driver, register_aws_domain
from utils.driver import convert_instance_state, sanitize_project_name
from utils.dynamic_name import rehash_dynamic_name
from utils.logger import log_msg
from utils.provider import get_specific_config, get_provider_dns_zones
from utils.list import unmarshall_list_array
from utils.aws_client import get_driver_access_key_id, get_driver_secret_access_key, create_aws_bucket, create_aws_registry, delete_aws_user_bucket, delete_aws_user_registry, get_aws_bucket_name, get_aws_registry_name, update_aws_bucket_credentials, update_aws_registry_credentials, get_driver_access_key_id, get_driver_secret_access_key 

CACHE_ADAPTER = get_adapter('cache')

class AwsDriver(ProviderDriver):
    def create_dns_records(self, record_name, environment, ip_address, root_dns_zone):
        register_aws_domain(record_name, environment['path'], ip_address, root_dns_zone)
        for subdomain in unmarshall_list_array(environment['subdomains']):
            dns_record_name = "{}.{}".format(subdomain, record_name)
            register_aws_domain(dns_record_name, environment['path'], ip_address, root_dns_zone)

    def create_instance(self, hashed_instance_name, environment, instance_region, instance_zone, instance_type, ami_image, generate_dns, root_dns_zone):
        def create_pulumi_program():
            aws_sg_id = get_specific_config('aws', 'sg', instance_region, instance_zone)
            aws_subnet_id = get_specific_config('aws', 'subnet', instance_region, instance_zone)
            aws_driver_access_key_id = get_driver_access_key_id()
            aws_driver_secret_access_key = get_driver_secret_access_key()
            provider = aws.Provider("instance-provider", region = instance_region, access_key = aws_driver_access_key_id, secret_key = aws_driver_secret_access_key)
            eip = aws.ec2.Eip(resource_name = hashed_instance_name, tags = { "Name": f"ip-{hashed_instance_name}"})
            ec2_instance = aws.ec2.Instance(resource_name = hashed_instance_name,
                opts = pulumi.ResourceOptions(provider = provider),
                instance_type = instance_type,
                availability_zone = "{}{}".format(instance_region, instance_zone),
                associate_public_ip_address = True,
                ami = ami_image,
                subnet_id = aws_subnet_id,
                vpc_security_group_ids = [ aws_sg_id ],
                tags = { "Name": hashed_instance_name },
                user_data = (lambda path: open(path).read())(self.cloud_init_script()))

            aws.ec2.EipAssociation(f"associating-{hashed_instance_name}", instance_id = ec2_instance.id, allocation_id = eip.id)
            if is_true(generate_dns):
                dns_driver = get_dns_zone_driver(root_dns_zone)
                ProviderDriverModule = importlib.import_module('drivers.{}'.format(dns_driver))
                ProviderDriver = getattr(ProviderDriverModule, dns_driver)
                ProviderDriver().create_dns_records(hashed_instance_name, environment, eip.public_ip, root_dns_zone)
            pulumi.export("public_ip", eip.public_ip)

        aws_driver_access_key_id = get_driver_access_key_id()
        aws_driver_secret_access_key = get_driver_secret_access_key()
        cloudflare_api_token = os.getenv('CLOUDFLARE_API_TOKEN')

        stack = auto.create_or_select_stack(stack_name = hashed_instance_name,
                                            project_name = sanitize_project_name(environment['path']),
                                            program = create_pulumi_program)
        stack.set_config("aws:accessKey", auto.ConfigValue(aws_driver_access_key_id))
        stack.set_config("aws:secretKey", auto.ConfigValue(aws_driver_secret_access_key))
        stack.set_config("aws:region", auto.ConfigValue(instance_region))
        if is_not_empty(cloudflare_api_token):
            stack.set_config("cloudflare:api_token", auto.ConfigValue(cloudflare_api_token))
        up_res = stack.up()

        return {
            "ip": up_res.outputs.get("public_ip").value
        }

    def refresh_instance(self, hashed_instance_name, environment, instance_region, instance_zone):
        return {}

    def get_server_state(self, server):
        switcher = {
            "running": "running",
            "shutting-down": "stopped",
            "stopping": "stopped",
            "stopped": "stopped",
            "terminated": "deleted"
        }

        return convert_instance_state(switcher, server)

    def get_virtual_machine(self, region, zone, instance_name):
        my_config = Config(
        region_name = region,
        signature_version = 'v4',
        retries = {
            'max_attempts': 10,
            'mode': 'standard'
        })
        client = boto3.client('ec2', config = my_config, aws_access_key_id = get_driver_access_key_id(), aws_secret_access_key = get_driver_secret_access_key())
        response = client.describe_instances( Filters = [ {'Name': 'tag: Name', 'Values': [instance_name]} ])
        instance_existance = response['Reservations'][0]['Instances'][0]
        aws_server = {
            "id": instance_existance['InstanceId'],
            "state": instance_existance['State']['Name']
        }
        if len(list(instance_existance)) > 0:
            return aws_server
        else:
            return None

    def update_virtual_machine_status(self, region, zone, server_id, action):
        my_config = Config(
        region_name = region,
        signature_version = 'v4',
        retries = {
            'max_attempts': 10,
            'mode': 'standard'
        })
        client = boto3.client('ec2', config = my_config, aws_access_key_id = get_driver_access_key_id(), aws_secret_access_key = get_driver_secret_access_key())
        if action == "poweroff":
            client.stop_instances(InstanceIds = [server_id])
        elif action == "reboot":
            client.reboot_instances(InstanceIds = [server_id])
        elif action == "poweron":
            client.start_instances(InstanceIds = [server_id])

    def create_bucket(self, user_email, hashed_bucket_name, region, bucket_type):
        def create_pulumi_program():
            aws.s3.Bucket(resource_name = hashed_bucket_name, acl = bucket_type if bucket_type == "private" else None, hosted_zone_id = region, tags = {"Name": hashed_bucket_name})
        aws_driver_access_key_id = get_driver_access_key_id()
        aws_driver_secret_access_key = get_driver_secret_access_key()
        stack = auto.create_or_select_stack(stack_name = hashed_bucket_name,
                                            project_name = sanitize_project_name(user_email),
                                            program = create_pulumi_program)

        stack.set_config("aws:accessKey", auto.ConfigValue(aws_driver_access_key_id))
        stack.set_config("aws:secretKey", auto.ConfigValue(aws_driver_secret_access_key))
        stack.set_config("aws:region", auto.ConfigValue(region))
        try:
            stack.up()
        except Exception as e:
            log_msg("ERROR", "[AwsDriver][create_bucket] unexpected exception : e = {}".format(e))

        aws_bucket_name = get_aws_bucket_name(hashed_bucket_name, region)
        bucket_endpoint = f'{aws_bucket_name}.s3.{region}.amazonaws.com/'
        (access_key, secret_key) = create_aws_bucket(hashed_bucket_name, region = region)
        CACHE_ADAPTER().put(f'aws_bucket_{hashed_bucket_name}', aws_bucket_name, 24)

        return {
            "endpoint": bucket_endpoint,
            "access_key": access_key,
            "secret_key": secret_key,
            "status": "active"
        }

    def update_bucket_credentials(self, bucket):
        bucket_hashed_name = rehash_dynamic_name(bucket.name, bucket.hash)
        (aws_access_key_id, aws_secret_access_key) = update_aws_bucket_credentials(bucket.id, bucket.region, bucket_hashed_name)
        return {
            "access_key": aws_access_key_id,
            "secret_key": aws_secret_access_key
        }

    def delete_bucket(self, bucket, user_email):
        hashed_bucket_name = rehash_dynamic_name(bucket.name, bucket.hash)
        stack = auto.select_stack(hashed_bucket_name, sanitize_project_name(user_email), program = self.delete_bucket)
        stack.destroy()
        delete_aws_user_bucket(bucket.region, bucket.id, hashed_bucket_name)

    def create_registry(self, user_email, hashed_name, region, type):
        def create_pulumi_program():
            aws_driver_access_key_id = get_driver_access_key_id()
            aws_driver_secret_access_key = get_driver_secret_access_key()
            provider = aws.Provider("registry-provider", region = region, access_key = aws_driver_access_key_id, secret_key = aws_driver_secret_access_key)
            registry = aws.ecr.Repository(resource_name = hashed_name, tags = {"Name": hashed_name}, opts = pulumi.ResourceOptions(provider = provider))
            pulumi.export("endpoint", registry.repository_url)

        aws_driver_access_key_id = get_driver_access_key_id()
        aws_driver_secret_access_key = get_driver_secret_access_key()
        stack = auto.create_or_select_stack(stack_name = hashed_name,
                                            project_name = sanitize_project_name(user_email),
                                            program = create_pulumi_program)
        stack.set_config("aws:accessKey", auto.ConfigValue(aws_driver_access_key_id))
        stack.set_config("aws:secretKey", auto.ConfigValue(aws_driver_secret_access_key))
        stack.set_config("aws:region", auto.ConfigValue(region))
        up_res = stack.up()
        (access_key, secret_key) = create_aws_registry(hashed_name, region)
        rg_name = get_aws_registry_name(hashed_name, region)
        CACHE_ADAPTER().put(f'aws_registry_{hashed_name}', rg_name, 24)

        return {
            "endpoint": up_res.outputs.get("endpoint").value,
            "access_key": access_key,
            "secret_key": secret_key,
            "status": "active"
        }

    def update_registry_credentials(self, registry):
        hashed_name = rehash_dynamic_name(registry.name, registry.hash)
        (aws_access_key_id, aws_secret_access_key) = update_aws_registry_credentials( registry.id, registry.region, hashed_name)
        return {
            "access_key": aws_access_key_id,
            "secret_key": aws_secret_access_key
        }

    def delete_registry(self, registry, user_email):
        hashed_name = rehash_dynamic_name(registry.name, registry.hash)
        stack = auto.select_stack(hashed_name, sanitize_project_name(user_email), program = self.delete_registry)
        stack.destroy()
        delete_aws_user_registry(hashed_name, registry.region, registry.id)

    def refresh_registry(self, user_email, hashed_registry_name):
        log_msg("INFO", "[AwsDriver][refresh_registry] user_email = {}, hashed_registry_name = {}".format(user_email, hashed_registry_name))
        return {}

    def refresh_bucket(self, user_email, hashed_bucket_name):
        log_msg("INFO", "[AwsDriver][refresh_bucket] user_email = {}, hashed_bucket_name = {}".format(user_email, hashed_bucket_name))
        return {}

    def cloud_init_script(self):
        return"cloud-init.yml"

    def create_custom_dns_record(self, record_name, dns_zone, record_type, ttl, data):
        def create_pulumi_program():            
            selected_zone = aws.route53.get_zone(name=dns_zone,private_zone=False)
            # Name the stack by the name of the record (the fully qualified name)
            resource_name=f"{record_name}.{dns_zone}"
            record = aws.route53.Record(resource_name,
                zone_id=selected_zone.zone_id,
                name=record_name,
                type=record_type,
                ttl=ttl,
                records=[data])
            pulumi.export("record",record)
        
        aws_driver_access_key_id = get_driver_access_key_id()
        aws_driver_secret_access_key = get_driver_secret_access_key()

        stack_name = f"{record_name}.{dns_zone}"
        stack = auto.create_stack(stack_name = stack_name,
                                project_name = os.getenv("PULUMI_AWS_PROJECT_NAME"),
                                program=create_pulumi_program)   
        
        stack.set_config("aws:accessKey", auto.ConfigValue(aws_driver_access_key_id))
        stack.set_config("aws:secretKey", auto.ConfigValue(aws_driver_secret_access_key))
        stack.set_config("aws:region", auto.ConfigValue(value="us-east-1"))

        stack.up(on_output=print)

        return {"record": record_name, "zone": dns_zone, "type": record_type, "ttl": ttl, "data": data}
    
    
    def delete_dns_records(self, record_id, record_name, dns_zone):
        project_name = os.getenv("PULUMI_AWS_PROJECT_NAME")
        stack_name = record_name
        stack = auto.select_stack(stack_name = stack_name,
                                project_name = project_name,
                                program=self.delete_dns_records)

        aws_driver_access_key_id = get_driver_access_key_id()
        aws_driver_secret_access_key = get_driver_secret_access_key()

        stack.set_config("aws:accessKey", auto.ConfigValue(aws_driver_access_key_id))
        stack.set_config("aws:secretKey", auto.ConfigValue(aws_driver_secret_access_key))
        stack.set_config("aws:region", auto.ConfigValue(value="us-east-1"))

        stack.destroy(on_output=print)
        stack.workspace.remove_stack(stack_name)
        
        return {"id": record_id, "record": record_name, "zone": dns_zone}

    def list_dns_records(self):
        aws_driver_access_key_id = get_driver_access_key_id()
        aws_driver_secret_access_key = get_driver_secret_access_key()

        my_config = Config(
                    signature_version = 'v4',
                    retries = {
                        'max_attempts': 10,
                        'mode': 'standard'
                    })
        route53 = boto3.client('route53', config=my_config,aws_access_key_id = aws_driver_access_key_id, aws_secret_access_key = aws_driver_secret_access_key)
            
        zones =  get_provider_dns_zones("aws")
        records = []
        for zone in zones:
            zone_boto3=route53.list_hosted_zones_by_name(DNSName=zone)
            zone_id=zone_boto3['HostedZones'][0]['Id']
            records_boto3 = route53.list_resource_record_sets(HostedZoneId=zone_id,)
            record_sets=records_boto3["ResourceRecordSets"]
            
            for record in record_sets:
                if record['Name'].endswith('.'):
                    record_name = record['Name'][:-1]
                else: 
                    record_name=record['Name']
                if record['Type']=="A":
                    records.append({
                        'id': record_sets.index(record),
                        'zone': zone,
                        'record': record_name,
                        'type': record['Type'],
                        'ttl': record.get('TTL','-'),
                        'data': record['AliasTarget']["DNSName"]
                    })
                if record['Type'] in ["NS","SOA", "CNAME"]:
                    values = [value['Value'] for value in record['ResourceRecords']]
                    records.append({
                        'id': record_sets.index(record),
                        'zone': zone,
                        'record': record_name,
                        'type': record['Type'],
                        'ttl': record.get('TTL','-'),
                        'data': values})

        return records
