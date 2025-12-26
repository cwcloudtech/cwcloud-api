def import_resources(app):
    import os
    import api_root
    from routes.ping import api_ping
    from routes.manifest import api_manifest
    from routes.error import api_error
    from routes.user import api_user
    from routes.user.reset_password import api_reset_password
    from routes.auth import api_auth
    from middleware import auth_guard
    from routes.access import api_access
    from routes.ai import api_prompt
    from routes.ai import api_adapter
    from routes.api_keys import api_keys
    from routes.bucket import api_bucket
    from routes.contact import api_contact
    from routes.contact_form import api_contact_form, api_contact_request
    from routes.control import api_control
    from routes.dns_zones import api_dns_zones
    from routes.email import api_email
    from routes.environment import api_environment
    from routes.instance import api_instance
    from routes.instance_types import api_instance_types
    from routes.mfa import api_mfa
    from routes.pricing import api_pricing
    from routes.project import api_project
    from routes.provider import api_provider
    from routes.registry import api_registry
    from routes.support import api_support
    from routes.faas import api_invocation, api_webhook as api_faas_webhook, api_functions, api_languages, api_templates, api_trigger_kinds, api_trigger
    from routes.config import api_config
    from routes.admin.user import api_admin_user
    from routes.admin.bucket import api_admin_bucket
    from routes.admin.faas import api_admin_invocation, api_admin_functions, api_admin_trigger
    from routes.admin.email import api_admin_email
    from routes.admin.environment import api_admin_environment
    from routes.admin.instance import api_admin_instance
    from routes.admin.mfa import api_admin_mfa
    from routes.admin.project import api_admin_project
    from routes.admin.registry import api_admin_registry
    from routes.admin.support import api_admin_support
    from routes.admin.kubernetes import api_admin_object, api_admin_cluster
    from routes.kubernetes import api_cluster, api_deployments
    from routes.iot import api_object_type
    from routes.iot import api_device
    from routes.iot import api_data
    from routes.storage import api_kv
    from routes.admin.iot import api_admin_object_type
    from routes.admin.iot import api_admin_device
    from routes.admin.iot import api_admin_data
    from routes.admin.dns import api_admin_dns
    from routes.monitor import api_monitor
    from routes.tracker import api_tracker
    from routes.admin.contact_form import api_admin_contact_form
    from routes.admin.monitor import api_admin_monitor
    from routes.admin.ai import api_admin_prompt
    from routes.admin.ai import api_admin_adapter
    from routes.admin.storage import api_admin_kv
    
    version = os.getenv('API_VERSION', 'v1')

    app.include_router(api_root.router, tags = ['Informations and Health checks'], prefix = f'/{version}/health')
    app.include_router(api_ping.router, tags = ['Informations and Health checks'], prefix = f'/{version}/ping')
    app.include_router(api_manifest.router, tags = ['Informations and Health checks'], prefix = f'/{version}/manifest')
    app.include_router(api_error.router, tags = ['Errors testing'], prefix = f'/{version}/error')
    app.include_router(auth_guard.router, tags = ['Authentication'], prefix = f'/{version}/auth')
    app.include_router(api_auth.router, tags = ['Authentication'], prefix = f'/{version}/auth')
    app.include_router(api_reset_password.router, tags = ['Authentication'], prefix = f'/{version}/admin')
    app.include_router(api_user.router, tags = ['User'], prefix = f'/{version}/user')
    app.include_router(api_mfa.router, tags = ['Multi-Factor Authentication'], prefix = f'/{version}/mfa')
    app.include_router(api_keys.router, tags = ['API Keys'], prefix = f'/{version}/api_keys')
    app.include_router(api_access.router, tags = ['Access'], prefix = f'/{version}/access')
    app.include_router(api_config.router, tags = ['Config'], prefix = f'/{version}/config')
    app.include_router(api_provider.router, tags = ['Provider'], prefix = f'/{version}/provider')
    app.include_router(api_dns_zones.router, tags = ['DNS Zones'], prefix = f'/{version}/dns_zones')
    app.include_router(api_environment.router, tags = ['Environment'], prefix = f'/{version}/environment')
    app.include_router(api_project.router, tags = ['Project'], prefix = f'/{version}/project')
    app.include_router(api_instance.router, tags = ['Instance'], prefix = f'/{version}/instance')
    app.include_router(api_instance_types.router, tags = ['Instance'], prefix = f'/{version}')
    app.include_router(api_control.router, tags = ['Instance'], prefix = f'/{version}/control')
    app.include_router(api_bucket.router, tags = ['Bucket'], prefix = f'/{version}/bucket')
    app.include_router(api_registry.router, tags = ['Registry'], prefix = f'/{version}/registry')
    app.include_router(api_email.router, tags = ['Email'], prefix = f'/{version}/email')
    app.include_router(api_languages.router, tags = ['FaaS'], prefix = f'/{version}/faas')
    app.include_router(api_functions.router, tags = ['FaaS'], prefix = f'/{version}/faas')
    app.include_router(api_templates.router, tags = ['FaaS'], prefix = f'/{version}/faas')
    app.include_router(api_invocation.router, tags = ['FaaS'], prefix = f'/{version}/faas')
    app.include_router(api_faas_webhook.router, tags = ['FaaS'], prefix = f'/{version}/faas')
    app.include_router(api_trigger_kinds.router, tags = ['FaaS'], prefix = f'/{version}/faas')
    app.include_router(api_trigger.router, tags = ['Faas'], prefix = f'/{version}/faas')
    app.include_router(api_adapter.router, tags = ['AI'], prefix = f'/{version}/ai')
    app.include_router(api_prompt.router, tags = ['AI'], prefix = f'/{version}/ai')
    app.include_router(api_deployments.router, tags = ['Kubernetes Apps deployments'], prefix = f'/{version}/kubernetes/deployment')
    app.include_router(api_object_type.router, tags = ['IoT'], prefix = f'/{version}/iot')
    app.include_router(api_device.router, tags = ['IoT'], prefix = f'/{version}/iot')
    app.include_router(api_data.router, tags = ['IoT'], prefix = f'/{version}/iot')
    app.include_router(api_kv.router, tags = ['Storage'], prefix = f'/{version}/storage/kv')
    app.include_router(api_monitor.router, tags = ['Observability'], prefix = f'/{version}/monitor')
    app.include_router(api_tracker.router, tags = ['Observability'], prefix = f'/{version}/tracker')
    app.include_router(api_contact_form.router, tags = ['Contact forms'], prefix = f'/{version}/contactform')
    app.include_router(api_contact_request.router, tags = ['Contact forms'], prefix = f'/{version}/contactreq')
    app.include_router(api_contact.router, tags = ['Contact and Support'], prefix = f'/{version}/contact')
    app.include_router(api_support.router, tags = ['Contact and Support'], prefix = f'/{version}/support')
    app.include_router(api_pricing.router, tags = ['Pricing'])
    app.include_router(api_admin_user.router, tags = ['Admin User'], prefix = f'/{version}/admin/user')
    app.include_router(api_admin_mfa.router, tags = ['Admin Multi-Factor Authentication'], prefix = f'/{version}/admin/mfa')
    app.include_router(api_admin_environment.router, tags = ['Admin Environment'], prefix = f'/{version}/admin/environment')
    app.include_router(api_admin_project.router, tags = ['Admin Project'], prefix = f'/{version}/admin/project')
    app.include_router(api_admin_instance.router, tags = ['Admin Instance'], prefix = f'/{version}/admin/instance')
    app.include_router(api_admin_bucket.router, tags = ['Admin Bucket'], prefix = f'/{version}/admin/bucket')
    app.include_router(api_admin_registry.router, tags = ['Admin Registry'], prefix = f'/{version}/admin/registry')
    app.include_router(api_admin_functions.router, tags = ['Admin FaaS'], prefix = f'/{version}/admin/faas')
    app.include_router(api_admin_invocation.router, tags = ['Admin FaaS'], prefix = f'/{version}/admin/faas')
    app.include_router(api_admin_trigger.router, tags = ['Admin FaaS'], prefix = f'/{version}/admin/faas')
    app.include_router(api_cluster.router, tags = ['Kubernetes Clusters'], prefix = f'/{version}/kubernetes/cluster')
    app.include_router(api_admin_cluster.router, tags = ['Admin Kubernetes Clusters'], prefix = f'/{version}/admin/kubernetes/cluster')
    app.include_router(api_admin_object.router, tags = ['Admin Kubernetes Objects'], prefix = f'/{version}/admin/kubernetes/object')
    app.include_router(api_admin_object_type.router, tags = ['Admin IoT'], prefix = f'/{version}/admin/iot')
    app.include_router(api_admin_device.router, tags = ['Admin IoT'], prefix = f'/{version}/admin/iot')
    app.include_router(api_admin_data.router, tags = ['Admin IoT'], prefix = f'/{version}/admin/iot')
    app.include_router(api_admin_monitor.router, tags = ['Admin Monitor'], prefix = f'/{version}/admin/monitor')
    app.include_router(api_admin_contact_form.router, tags = ['Admin Contact Form'], prefix = f'/{version}/admin/contactform')
    app.include_router(api_admin_email.router, tags = ['Admin Email'], prefix = f'/{version}/admin/email')
    app.include_router(api_admin_support.router, tags = ['Admin Support Tickets'], prefix = f'/{version}/admin/support')
    app.include_router(api_admin_dns.router, tags = ['Admin DNS'], prefix = f'/{version}/admin/dns')
    app.include_router(api_admin_prompt.router, tags = ['Admin AI'], prefix = f'/{version}/admin/ai')
    app.include_router(api_admin_adapter.router, tags = ['Admin AI'], prefix = f'/{version}/admin/ai')
    app.include_router(api_admin_kv.router, tags = ['Admin Storage'], prefix = f'/{version}/admin/storage/kv')
