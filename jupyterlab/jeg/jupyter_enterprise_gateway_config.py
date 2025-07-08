# Configuration file for jupyter-enterprise-gateway.

c = get_config()  #noqa

#------------------------------------------------------------------------------
# Application(SingletonConfigurable) configuration
#------------------------------------------------------------------------------
## This is an application.

## The date format used by logging formatters for %(asctime)s
#  Default: '%Y-%m-%d %H:%M:%S'
# c.Application.log_datefmt = '%Y-%m-%d %H:%M:%S'

## The Logging format template
#  Default: '[%(name)s]%(highlevel)s %(message)s'
# c.Application.log_format = '[%(name)s]%(highlevel)s %(message)s'

## Set the log level by value or name.
#  Choices: any of [0, 10, 20, 30, 40, 50, 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']
#  Default: 30
# c.Application.log_level = 30

## Configure additional log handlers.
#  
#  The default stderr logs handler is configured by the log_level, log_datefmt
#  and log_format settings.
#  
#  This configuration can be used to configure additional handlers (e.g. to
#  output the log to a file) or for finer control over the default handlers.
#  
#  If provided this should be a logging configuration dictionary, for more
#  information see:
#  https://docs.python.org/3/library/logging.config.html#logging-config-
#  dictschema
#  
#  This dictionary is merged with the base logging configuration which defines
#  the following:
#  
#  * A logging formatter intended for interactive use called
#    ``console``.
#  * A logging handler that writes to stderr called
#    ``console`` which uses the formatter ``console``.
#  * A logger with the name of this application set to ``DEBUG``
#    level.
#  
#  This example adds a new handler that writes to a file:
#  
#  .. code-block:: python
#  
#     c.Application.logging_config = {
#         "handlers": {
#             "file": {
#                 "class": "logging.FileHandler",
#                 "level": "DEBUG",
#                 "filename": "<path/to/file>",
#             }
#         },
#         "loggers": {
#             "<application-name>": {
#                 "level": "DEBUG",
#                 # NOTE: if you don't list the default "console"
#                 # handler here then it will be disabled
#                 "handlers": ["console", "file"],
#             },
#         },
#     }
#  Default: {}
# c.Application.logging_config = {}

## Instead of starting the Application, dump configuration to stdout
#  Default: False
# c.Application.show_config = False

## Instead of starting the Application, dump configuration to stdout (as JSON)
#  Default: False
# c.Application.show_config_json = False

#------------------------------------------------------------------------------
# JupyterApp(Application) configuration
#------------------------------------------------------------------------------
## Base class for Jupyter applications

## Answer yes to any prompts.
#  Default: False
# c.JupyterApp.answer_yes = False

## Full path of a config file.
#  Default: ''
# c.JupyterApp.config_file = ''

## Specify a config file to load.
#  Default: ''
# c.JupyterApp.config_file_name = ''

## Generate default config file.
#  Default: False
# c.JupyterApp.generate_config = False

## The date format used by logging formatters for %(asctime)s
#  See also: Application.log_datefmt
# c.JupyterApp.log_datefmt = '%Y-%m-%d %H:%M:%S'

## The Logging format template
#  See also: Application.log_format
# c.JupyterApp.log_format = '[%(name)s]%(highlevel)s %(message)s'

## Set the log level by value or name.
#  See also: Application.log_level
# c.JupyterApp.log_level = 30

## 
#  See also: Application.logging_config
# c.JupyterApp.logging_config = {}

## Instead of starting the Application, dump configuration to stdout
#  See also: Application.show_config
# c.JupyterApp.show_config = False

## Instead of starting the Application, dump configuration to stdout (as JSON)
#  See also: Application.show_config_json
# c.JupyterApp.show_config_json = False

#------------------------------------------------------------------------------
# EnterpriseGatewayConfigMixin(Configurable) configuration
#------------------------------------------------------------------------------
## A mixin for enterprise gateway config.

## Sets the Access-Control-Allow-Credentials header. (EG_ALLOW_CREDENTIALS env
#  var)
#  Default: ''
# c.EnterpriseGatewayConfigMixin.allow_credentials = ''

## Sets the Access-Control-Allow-Headers header. (EG_ALLOW_HEADERS env var)
#  Default: ''
# c.EnterpriseGatewayConfigMixin.allow_headers = ''

## Sets the Access-Control-Allow-Methods header. (EG_ALLOW_METHODS env var)
#  Default: ''
# c.EnterpriseGatewayConfigMixin.allow_methods = ''

## Sets the Access-Control-Allow-Origin header. (EG_ALLOW_ORIGIN env var)
#  Default: ''
# c.EnterpriseGatewayConfigMixin.allow_origin = ''

## The http url specifying the alternate YARN Resource Manager.  This value should
#                                  be set when YARN Resource Managers are configured for high availability.  Note: If both
#                                  YARN endpoints are NOT set, the YARN library will use the files within the local
#                                  HADOOP_CONFIG_DIR to determine the active resource manager.
#                                  (EG_ALT_YARN_ENDPOINT env var)
#  Default: None
# c.EnterpriseGatewayConfigMixin.alt_yarn_endpoint = None

## Authorization token required for all requests (EG_AUTH_TOKEN env var)
#  Default: ''
# c.EnterpriseGatewayConfigMixin.auth_token = ''

## Hostname (e.g. 'localhost', 'reverse.proxy.net') which the handler will match
#                                  against the request's SSL certificate.  An HTTP 403 (Forbidden) error will be raised on
#                                  a failed match.  This option requires TLS to be enabled.  It does not support IP
#                                  addresses. (EG_AUTHORIZED_ORIGIN env var)
#  Default: ''
# c.EnterpriseGatewayConfigMixin.authorized_origin = ''

## Comma-separated list of user names (e.g., ['bob','alice']) against which
#                             KERNEL_USERNAME will be compared.  Any match (case-sensitive) will allow the kernel's
#                             launch, otherwise an HTTP 403 (Forbidden) error will be raised.  The set of unauthorized
#                             users takes precedence. This option should be used carefully as it can dramatically limit
#                             who can launch kernels.  (EG_AUTHORIZED_USERS env var - non-bracketed,
#                             just comma-separated)
#  Default: set()
# c.EnterpriseGatewayConfigMixin.authorized_users = set()

## Specifies the type of availability.  Values must be one of "standalone" or "replication".
#                  (EG_AVAILABILITY_MODE env var)
#  Choices: any of ['replication', 'standalone'] (case-insensitive) or None
#  Default: None
# c.EnterpriseGatewayConfigMixin.availability_mode = None

## The base path for mounting all API resources (EG_BASE_URL env var)
#  Default: '/'
# c.EnterpriseGatewayConfigMixin.base_url = '/'

## The full path to an SSL/TLS certificate file. (EG_CERTFILE env var)
#  Default: None
# c.EnterpriseGatewayConfigMixin.certfile = None

## The full path to a certificate authority certificate for SSL/TLS
#                          client authentication. (EG_CLIENT_CA env var)
#  Default: None
# c.EnterpriseGatewayConfigMixin.client_ca = None

## Environment variables allowed to be set when a client requests a
#                                 new kernel. (EG_CLIENT_ENVS env var)
#  Default: []
# c.EnterpriseGatewayConfigMixin.client_envs = []

## The http url for accessing the Conductor REST API.
#                                   (EG_CONDUCTOR_ENDPOINT env var)
#  Default: None
# c.EnterpriseGatewayConfigMixin.conductor_endpoint = None

## Default kernel name when spawning a kernel (EG_DEFAULT_KERNEL_NAME env var)
#  Default: ''
# c.EnterpriseGatewayConfigMixin.default_kernel_name = ''

## Specifies the number of seconds configuration files are polled for
#                                        changes.  A value of 0 or less disables dynamic config updates.
#                                        (EG_DYNAMIC_CONFIG_INTERVAL env var)
#  Default: 0
# c.EnterpriseGatewayConfigMixin.dynamic_config_interval = 0

## DEPRECATED, use inherited_envs
#  Default: []
# c.EnterpriseGatewayConfigMixin.env_process_whitelist = []

## DEPRECATED, use client_envs.
#  Default: []
# c.EnterpriseGatewayConfigMixin.env_whitelist = []

## Sets the Access-Control-Expose-Headers header. (EG_EXPOSE_HEADERS env var)
#  Default: ''
# c.EnterpriseGatewayConfigMixin.expose_headers = ''

## Indicates whether impersonation will be performed during kernel launch.
#                                   (EG_IMPERSONATION_ENABLED env var)
#  Default: False
# c.EnterpriseGatewayConfigMixin.impersonation_enabled = False

## Environment variables allowed to be inherited
#                                  from the spawning process by the kernel. (EG_INHERITED_ENVS env var)
#  Default: []
# c.EnterpriseGatewayConfigMixin.inherited_envs = []

## IP address on which to listen (EG_IP env var)
#  Default: '127.0.0.1'
# c.EnterpriseGatewayConfigMixin.ip = '127.0.0.1'

## Request headers to make available to kernel launch framework.
#                            (EG_KERNEL_HEADERS env var)
#  Default: []
# c.EnterpriseGatewayConfigMixin.kernel_headers = []

## The kernel manager class to use. Must be a subclass of
#  `enterprise_gateway.services.kernels.RemoteMappingKernelManager`.
#  Default: 'enterprise_gateway.services.kernels.remotemanager.RemoteMappingKernelManager'
# c.EnterpriseGatewayConfigMixin.kernel_manager_class = 'enterprise_gateway.services.kernels.remotemanager.RemoteMappingKernelManager'

## The kernel session manager class to use. Must be a subclass of
#  `enterprise_gateway.services.sessions.KernelSessionManager`.
#  Default: 'enterprise_gateway.services.sessions.kernelsessionmanager.FileKernelSessionManager'
# c.EnterpriseGatewayConfigMixin.kernel_session_manager_class = 'enterprise_gateway.services.sessions.kernelsessionmanager.FileKernelSessionManager'

## The kernel spec cache class to use. Must be a subclass of
#  `enterprise_gateway.services.kernelspecs.KernelSpecCache`.
#  Default: 'enterprise_gateway.services.kernelspecs.kernelspec_cache.KernelSpecCache'
# c.EnterpriseGatewayConfigMixin.kernel_spec_cache_class = 'enterprise_gateway.services.kernelspecs.kernelspec_cache.KernelSpecCache'

## The kernel spec manager class to use. Must be a subclass of
#  `jupyter_client.kernelspec.KernelSpecManager`.
#  Default: 'jupyter_client.kernelspec.KernelSpecManager'
# c.EnterpriseGatewayConfigMixin.kernel_spec_manager_class = 'jupyter_client.kernelspec.KernelSpecManager'

## The full path to a private key file for usage with SSL/TLS. (EG_KEYFILE env
#  var)
#  Default: None
# c.EnterpriseGatewayConfigMixin.keyfile = None

## Permits listing of the running kernels using API endpoints /api/kernels
#                          and /api/sessions. (EG_LIST_KERNELS env var) Note: Jupyter Notebook
#                          allows this by default but Jupyter Enterprise Gateway does not.
#  Default: False
# c.EnterpriseGatewayConfigMixin.list_kernels = False

## Specifies which load balancing algorithm DistributedProcessProxy should use.
#              Must be one of "round-robin" or "least-connection".  (EG_LOAD_BALANCING_ALGORITHM
#              env var)
#  Default: 'round-robin'
# c.EnterpriseGatewayConfigMixin.load_balancing_algorithm = 'round-robin'

## Sets the Access-Control-Max-Age header. (EG_MAX_AGE env var)
#  Default: ''
# c.EnterpriseGatewayConfigMixin.max_age = ''

## Limits the number of kernel instances allowed to run by this gateway.
#                            Unbounded by default. (EG_MAX_KERNELS env var)
#  Default: None
# c.EnterpriseGatewayConfigMixin.max_kernels = None

## Specifies the maximum number of kernels a user can have active
#                                     simultaneously.  A value of -1 disables enforcement.
#                                     (EG_MAX_KERNELS_PER_USER env var)
#  Default: -1
# c.EnterpriseGatewayConfigMixin.max_kernels_per_user = -1

## Port on which to listen (EG_PORT env var)
#  Default: 8888
# c.EnterpriseGatewayConfigMixin.port = 8888

## Specifies the lower and upper port numbers from which ports are created.
#                           The bounded values are separated by '..' (e.g., 33245..34245 specifies a range of 1000 ports
#                           to be randomly selected). A range of zero (e.g., 33245..33245 or 0..0) disables port-range
#                           enforcement.  (EG_PORT_RANGE env var)
#  Default: '0..0'
# c.EnterpriseGatewayConfigMixin.port_range = '0..0'

## Number of ports to try if the specified port is not available
#                             (EG_PORT_RETRIES env var)
#  Default: 50
# c.EnterpriseGatewayConfigMixin.port_retries = 50

## Bracketed comma-separated list of hosts on which DistributedProcessProxy
#                          kernels will be launched e.g., ['host1','host2']. (EG_REMOTE_HOSTS env var
#                          - non-bracketed, just comma-separated)
#  Default: ['localhost']
# c.EnterpriseGatewayConfigMixin.remote_hosts = ['localhost']

## Sets the SSL version to use for the web socket
#                            connection. (EG_SSL_VERSION env var)
#  Default: None
# c.EnterpriseGatewayConfigMixin.ssl_version = None

## Use x-* header values for overriding the remote-ip, useful when
#                             application is behind a proxy. (EG_TRUST_XHEADERS env var)
#  Default: False
# c.EnterpriseGatewayConfigMixin.trust_xheaders = False

## Comma-separated list of user names (e.g., ['root','admin']) against which
#                               KERNEL_USERNAME will be compared.  Any match (case-sensitive) will prevent the
#                               kernel's launch and result in an HTTP 403 (Forbidden) error.
#                               (EG_UNAUTHORIZED_USERS env var - non-bracketed, just comma-separated)
#  Default: {'root'}
# c.EnterpriseGatewayConfigMixin.unauthorized_users = {'root'}

## Specifies the ping interval(in seconds) that should be used by zmq port
#                                       associated with spawned kernels. Set this variable to 0 to disable ping mechanism.
#                                      (EG_WS_PING_INTERVAL_SECS env var)
#  Default: 30
# c.EnterpriseGatewayConfigMixin.ws_ping_interval = 30

## The http url specifying the YARN Resource Manager. Note: If this value is NOT set,
#                              the YARN library will use the files within the local HADOOP_CONFIG_DIR to determine the
#                              active resource manager. (EG_YARN_ENDPOINT env var)
#  Default: None
# c.EnterpriseGatewayConfigMixin.yarn_endpoint = None

## Is YARN Kerberos/SPNEGO Security enabled (True/False).
#                                            (EG_YARN_ENDPOINT_SECURITY_ENABLED env var)
#  Default: False
# c.EnterpriseGatewayConfigMixin.yarn_endpoint_security_enabled = False

#------------------------------------------------------------------------------
# EnterpriseGatewayApp(EnterpriseGatewayConfigMixin, JupyterApp) configuration
#------------------------------------------------------------------------------
## Application that provisions Jupyter kernels and proxies HTTP/Websocket traffic
#  to the kernels.
#  
#  - reads command line and environment variable settings - initializes managers
#  and routes - creates a Tornado HTTP server - starts the Tornado event loop

## Sets the Access-Control-Allow-Credentials header. (EG_ALLOW_CREDENTIALS env
#  var)
#  See also: EnterpriseGatewayConfigMixin.allow_credentials
# c.EnterpriseGatewayApp.allow_credentials = ''

## Sets the Access-Control-Allow-Headers header. (EG_ALLOW_HEADERS env var)
#  See also: EnterpriseGatewayConfigMixin.allow_headers
# c.EnterpriseGatewayApp.allow_headers = ''

## Sets the Access-Control-Allow-Methods header. (EG_ALLOW_METHODS env var)
#  See also: EnterpriseGatewayConfigMixin.allow_methods
# c.EnterpriseGatewayApp.allow_methods = ''

## Sets the Access-Control-Allow-Origin header. (EG_ALLOW_ORIGIN env var)
#  See also: EnterpriseGatewayConfigMixin.allow_origin
# c.EnterpriseGatewayApp.allow_origin = ''

## The http url specifying the alternate YARN Resource Manager.  This value
#  should
#  See also: EnterpriseGatewayConfigMixin.alt_yarn_endpoint
# c.EnterpriseGatewayApp.alt_yarn_endpoint = None

## Answer yes to any prompts.
#  See also: JupyterApp.answer_yes
# c.EnterpriseGatewayApp.answer_yes = False

## Authorization token required for all requests (EG_AUTH_TOKEN env var)
#  See also: EnterpriseGatewayConfigMixin.auth_token
# c.EnterpriseGatewayApp.auth_token = ''

## Hostname (e.g. 'localhost', 'reverse.proxy.net') which the handler will match
#  See also: EnterpriseGatewayConfigMixin.authorized_origin
# c.EnterpriseGatewayApp.authorized_origin = ''

## Comma-separated list of user names (e.g., ['bob','alice']) against which
#  See also: EnterpriseGatewayConfigMixin.authorized_users
# c.EnterpriseGatewayApp.authorized_users = set()

## Specifies the type of availability.  Values must be one of "standalone" or
#  "replication".
#  See also: EnterpriseGatewayConfigMixin.availability_mode
# c.EnterpriseGatewayApp.availability_mode = None

## The base path for mounting all API resources (EG_BASE_URL env var)
#  See also: EnterpriseGatewayConfigMixin.base_url
# c.EnterpriseGatewayApp.base_url = '/'

## The full path to an SSL/TLS certificate file. (EG_CERTFILE env var)
#  See also: EnterpriseGatewayConfigMixin.certfile
# c.EnterpriseGatewayApp.certfile = None

## The full path to a certificate authority certificate for SSL/TLS
#  See also: EnterpriseGatewayConfigMixin.client_ca
# c.EnterpriseGatewayApp.client_ca = None

## Environment variables allowed to be set when a client requests a
#  See also: EnterpriseGatewayConfigMixin.client_envs
# c.EnterpriseGatewayApp.client_envs = []

## The http url for accessing the Conductor REST API.
#  See also: EnterpriseGatewayConfigMixin.conductor_endpoint
# c.EnterpriseGatewayApp.conductor_endpoint = None

## Full path of a config file.
#  See also: JupyterApp.config_file
# c.EnterpriseGatewayApp.config_file = ''

## Specify a config file to load.
#  See also: JupyterApp.config_file_name
# c.EnterpriseGatewayApp.config_file_name = ''

## Default kernel name when spawning a kernel (EG_DEFAULT_KERNEL_NAME env var)
#  See also: EnterpriseGatewayConfigMixin.default_kernel_name
# c.EnterpriseGatewayApp.default_kernel_name = ''

## Specifies the number of seconds configuration files are polled for
#  See also: EnterpriseGatewayConfigMixin.dynamic_config_interval
# c.EnterpriseGatewayApp.dynamic_config_interval = 0

## DEPRECATED, use inherited_envs
#  See also: EnterpriseGatewayConfigMixin.env_process_whitelist
# c.EnterpriseGatewayApp.env_process_whitelist = []

## DEPRECATED, use client_envs.
#  See also: EnterpriseGatewayConfigMixin.env_whitelist
# c.EnterpriseGatewayApp.env_whitelist = []

## Sets the Access-Control-Expose-Headers header. (EG_EXPOSE_HEADERS env var)
#  See also: EnterpriseGatewayConfigMixin.expose_headers
# c.EnterpriseGatewayApp.expose_headers = ''

## Generate default config file.
#  See also: JupyterApp.generate_config
# c.EnterpriseGatewayApp.generate_config = False

## Indicates whether impersonation will be performed during kernel launch.
#  See also: EnterpriseGatewayConfigMixin.impersonation_enabled
# c.EnterpriseGatewayApp.impersonation_enabled = False

## Environment variables allowed to be inherited
#  See also: EnterpriseGatewayConfigMixin.inherited_envs
# c.EnterpriseGatewayApp.inherited_envs = []

## IP address on which to listen (EG_IP env var)
#  See also: EnterpriseGatewayConfigMixin.ip
# c.EnterpriseGatewayApp.ip = '127.0.0.1'

## Request headers to make available to kernel launch framework.
#  See also: EnterpriseGatewayConfigMixin.kernel_headers
# c.EnterpriseGatewayApp.kernel_headers = []

## 
#  See also: EnterpriseGatewayConfigMixin.kernel_manager_class
# c.EnterpriseGatewayApp.kernel_manager_class = 'enterprise_gateway.services.kernels.remotemanager.RemoteMappingKernelManager'

## 
#  See also: EnterpriseGatewayConfigMixin.kernel_session_manager_class
# c.EnterpriseGatewayApp.kernel_session_manager_class = 'enterprise_gateway.services.sessions.kernelsessionmanager.FileKernelSessionManager'

## 
#  See also: EnterpriseGatewayConfigMixin.kernel_spec_cache_class
# c.EnterpriseGatewayApp.kernel_spec_cache_class = 'enterprise_gateway.services.kernelspecs.kernelspec_cache.KernelSpecCache'

## 
#  See also: EnterpriseGatewayConfigMixin.kernel_spec_manager_class
# c.EnterpriseGatewayApp.kernel_spec_manager_class = 'jupyter_client.kernelspec.KernelSpecManager'

## The full path to a private key file for usage with SSL/TLS. (EG_KEYFILE env
#  var)
#  See also: EnterpriseGatewayConfigMixin.keyfile
# c.EnterpriseGatewayApp.keyfile = None

## Permits listing of the running kernels using API endpoints /api/kernels
#  See also: EnterpriseGatewayConfigMixin.list_kernels
# c.EnterpriseGatewayApp.list_kernels = False

## Specifies which load balancing algorithm DistributedProcessProxy should use.
#  See also: EnterpriseGatewayConfigMixin.load_balancing_algorithm
# c.EnterpriseGatewayApp.load_balancing_algorithm = 'round-robin'

## The date format used by logging formatters for %(asctime)s
#  See also: Application.log_datefmt
# c.EnterpriseGatewayApp.log_datefmt = '%Y-%m-%d %H:%M:%S'

## The Logging format template
#  See also: Application.log_format
# c.EnterpriseGatewayApp.log_format = '[%(name)s]%(highlevel)s %(message)s'

## Set the log level by value or name.
#  See also: Application.log_level
# c.EnterpriseGatewayApp.log_level = 30

## 
#  See also: Application.logging_config
# c.EnterpriseGatewayApp.logging_config = {}

## Sets the Access-Control-Max-Age header. (EG_MAX_AGE env var)
#  See also: EnterpriseGatewayConfigMixin.max_age
# c.EnterpriseGatewayApp.max_age = ''

## Limits the number of kernel instances allowed to run by this gateway.
#  See also: EnterpriseGatewayConfigMixin.max_kernels
# c.EnterpriseGatewayApp.max_kernels = None

## Specifies the maximum number of kernels a user can have active
#  See also: EnterpriseGatewayConfigMixin.max_kernels_per_user
# c.EnterpriseGatewayApp.max_kernels_per_user = -1

## Port on which to listen (EG_PORT env var)
#  See also: EnterpriseGatewayConfigMixin.port
# c.EnterpriseGatewayApp.port = 8888

## Specifies the lower and upper port numbers from which ports are created.
#  See also: EnterpriseGatewayConfigMixin.port_range
# c.EnterpriseGatewayApp.port_range = '0..0'

## Number of ports to try if the specified port is not available
#  See also: EnterpriseGatewayConfigMixin.port_retries
# c.EnterpriseGatewayApp.port_retries = 50

## Bracketed comma-separated list of hosts on which DistributedProcessProxy
#  See also: EnterpriseGatewayConfigMixin.remote_hosts
# c.EnterpriseGatewayApp.remote_hosts = ['localhost']

## Instead of starting the Application, dump configuration to stdout
#  See also: Application.show_config
# c.EnterpriseGatewayApp.show_config = False

## Instead of starting the Application, dump configuration to stdout (as JSON)
#  See also: Application.show_config_json
# c.EnterpriseGatewayApp.show_config_json = False

## Sets the SSL version to use for the web socket
#  See also: EnterpriseGatewayConfigMixin.ssl_version
# c.EnterpriseGatewayApp.ssl_version = None

## Use x-* header values for overriding the remote-ip, useful when
#  See also: EnterpriseGatewayConfigMixin.trust_xheaders
# c.EnterpriseGatewayApp.trust_xheaders = False

## Comma-separated list of user names (e.g., ['root','admin']) against which
#  See also: EnterpriseGatewayConfigMixin.unauthorized_users
# c.EnterpriseGatewayApp.unauthorized_users = {'root'}

## Specifies the ping interval(in seconds) that should be used by zmq port
#  See also: EnterpriseGatewayConfigMixin.ws_ping_interval
# c.EnterpriseGatewayApp.ws_ping_interval = 30

## The http url specifying the YARN Resource Manager. Note: If this value is NOT
#  set,
#  See also: EnterpriseGatewayConfigMixin.yarn_endpoint
# c.EnterpriseGatewayApp.yarn_endpoint = None

## Is YARN Kerberos/SPNEGO Security enabled (True/False).
#  See also: EnterpriseGatewayConfigMixin.yarn_endpoint_security_enabled
# c.EnterpriseGatewayApp.yarn_endpoint_security_enabled = False

#------------------------------------------------------------------------------
# KernelSpecCache(SingletonConfigurable) configuration
#------------------------------------------------------------------------------
## The primary (singleton) instance for managing KernelSpecs.
#  
#      This class contains the configured KernelSpecManager instance upon
#      which it uses to populate the cache (when enabled) or as a pass-thru
#      (when disabled).
#  
#      Note that the KernelSpecManager returns different formats from methods
#      get_all_specs() and get_kernel_spec().  The format in which cache entries
#      are stored is that of the get_all_specs() results.  As a result, some
#      conversion between formats is necessary, depending on which method is called.

## Enable Kernel Specification caching. (EG_KERNELSPEC_CACHE_ENABLED env var)
#  Default: True
# c.KernelSpecCache.cache_enabled = True

#------------------------------------------------------------------------------
# KernelSessionManager(LoggingConfigurable) configuration
#------------------------------------------------------------------------------
## KernelSessionManager is used to save and load kernel sessions from persistent
#  storage.
#  
#  KernelSessionManager provides the basis for an HA solution.  It loads the
#  complete set of persisted kernel sessions during construction.  Following
#  construction the parent object calls start_sessions to allow Enterprise
#  Gateway to validate that all loaded sessions are still valid.  Those that it
#  cannot 'revive' are marked for deletion and the in-memory dictionary is
#  updated - and the entire collection is written to store (file or database).
#  
#  As kernels are created and destroyed, the KernelSessionManager is called upon
#  to keep kernel session state consistent.
#  
#  NOTE: This class is essentially an abstract base class that requires its
#  `load_sessions` and `save_sessions` have implementations in subclasses.
#  abc.MetaABC is not used due to conflicts with derivation of
#  LoggingConfigurable - which seemed more important.

## Enable kernel session persistence (True or False). Default = False
#  (EG_KERNEL_SESSION_PERSISTENCE env var)
#  Default: False
# c.KernelSessionManager.enable_persistence = False

## Identifies the root 'directory' under which the 'kernel_sessions' node will
#  reside.  This directory should exist.  (EG_PERSISTENCE_ROOT env var)
#  Default: ''
# c.KernelSessionManager.persistence_root = ''

#------------------------------------------------------------------------------
# FileKernelSessionManager(KernelSessionManager) configuration
#------------------------------------------------------------------------------
## Performs kernel session persistence operations against the file
#  `sessions.json` located in the kernel_sessions directory in the directory
#  pointed to by the persistence_root parameter (default JUPYTER_DATA_DIR).

## Enable kernel session persistence (True or False). Default = False
#  See also: KernelSessionManager.enable_persistence
# c.FileKernelSessionManager.enable_persistence = False

## Identifies the root 'directory' under which the 'kernel_sessions' node will
#  See also: KernelSessionManager.persistence_root
# c.FileKernelSessionManager.persistence_root = ''

#------------------------------------------------------------------------------
# WebhookKernelSessionManager(KernelSessionManager) configuration
#------------------------------------------------------------------------------
## Performs kernel session persistence operations against URL provided
#  (EG_WEBHOOK_URL). The URL must have 4 endpoints associated with it. 1 delete
#  endpoint that takes a list of kernel ids in the body, 1 post endpoint that
#  takes kernels id as a url param and the kernel session as the body, 1 get
#  endpoint that returns all kernel sessions, and 1 get endpoint that returns a
#  specific kernel session based on kernel id as url param.

## Authentication type for webhook kernel session manager API. Either basic,
#  digest or None
#  Choices: any of ['basic', 'digest'] (case-insensitive) or None
#  Default: None
# c.WebhookKernelSessionManager.auth_type = None

## Enable kernel session persistence (True or False). Default = False
#  See also: KernelSessionManager.enable_persistence
# c.WebhookKernelSessionManager.enable_persistence = False

## Identifies the root 'directory' under which the 'kernel_sessions' node will
#  See also: KernelSessionManager.persistence_root
# c.WebhookKernelSessionManager.persistence_root = ''

## Password for webhook kernel session manager API auth
#  Default: ''
# c.WebhookKernelSessionManager.webhook_password = ''

## URL endpoint for webhook kernel session manager
#  Default: ''
# c.WebhookKernelSessionManager.webhook_url = ''

## Username for webhook kernel session manager API auth
#  Default: ''
# c.WebhookKernelSessionManager.webhook_username = ''

#------------------------------------------------------------------------------
# MultiKernelManager(LoggingConfigurable) configuration
#------------------------------------------------------------------------------
## A class for managing multiple kernels.

## The name of the default kernel to start
#  Default: 'python3'
# c.MultiKernelManager.default_kernel_name = 'python3'

## The kernel manager class.  This is configurable to allow
#          subclassing of the KernelManager for customized behavior.
#  Default: 'jupyter_client.ioloop.IOLoopKernelManager'
# c.MultiKernelManager.kernel_manager_class = 'jupyter_client.ioloop.IOLoopKernelManager'

## Share a single zmq.Context to talk to all my kernels
#  Default: True
# c.MultiKernelManager.shared_context = True

#------------------------------------------------------------------------------
# AsyncMultiKernelManager(MultiKernelManager) configuration
#------------------------------------------------------------------------------
## The name of the default kernel to start
#  See also: MultiKernelManager.default_kernel_name
# c.AsyncMultiKernelManager.default_kernel_name = 'python3'

## The kernel manager class.  This is configurable to allow
#          subclassing of the AsyncKernelManager for customized behavior.
#  Default: 'jupyter_client.ioloop.AsyncIOLoopKernelManager'
# c.AsyncMultiKernelManager.kernel_manager_class = 'jupyter_client.ioloop.AsyncIOLoopKernelManager'

## Share a single zmq.Context to talk to all my kernels
#  See also: MultiKernelManager.shared_context
# c.AsyncMultiKernelManager.shared_context = True

#------------------------------------------------------------------------------
# MappingKernelManager(MultiKernelManager) configuration
#------------------------------------------------------------------------------
## A KernelManager that handles
#      - File mapping
#      - HTTP error handling
#      - Kernel message filtering

## Whether to send tracebacks to clients on exceptions.
#  Default: True
# c.MappingKernelManager.allow_tracebacks = True

## White list of allowed kernel message types.
#          When the list is empty, all message types are allowed.
#  Default: []
# c.MappingKernelManager.allowed_message_types = []

## Whether messages from kernels whose frontends have disconnected should be
#  buffered in-memory.
#  
#          When True (default), messages are buffered and replayed on reconnect,
#          avoiding lost messages due to interrupted connectivity.
#  
#          Disable if long-running kernels will produce too much output while
#          no frontends are connected.
#  Default: True
# c.MappingKernelManager.buffer_offline_messages = True

## Whether to consider culling kernels which are busy.
#          Only effective if cull_idle_timeout > 0.
#  Default: False
# c.MappingKernelManager.cull_busy = False

## Whether to consider culling kernels which have one or more connections.
#          Only effective if cull_idle_timeout > 0.
#  Default: False
# c.MappingKernelManager.cull_connected = False

## Timeout (in seconds) after which a kernel is considered idle and ready to be culled.
#          Values of 0 or lower disable culling. Very short timeouts may result in kernels being culled
#          for users with poor network connections.
#  Default: 0
# c.MappingKernelManager.cull_idle_timeout = 0

## The interval (in seconds) on which to check for idle kernels exceeding the
#  cull timeout value.
#  Default: 300
# c.MappingKernelManager.cull_interval = 300

## The name of the default kernel to start
#  See also: MultiKernelManager.default_kernel_name
# c.MappingKernelManager.default_kernel_name = 'python3'

## Timeout for giving up on a kernel (in seconds).
#  
#          On starting and restarting kernels, we check whether the
#          kernel is running and responsive by sending kernel_info_requests.
#          This sets the timeout in seconds for how long the kernel can take
#          before being presumed dead.
#          This affects the MappingKernelManager (which handles kernel restarts)
#          and the ZMQChannelsHandler (which handles the startup).
#  Default: 60
# c.MappingKernelManager.kernel_info_timeout = 60

## The kernel manager class.  This is configurable to allow
#  See also: MultiKernelManager.kernel_manager_class
# c.MappingKernelManager.kernel_manager_class = 'jupyter_client.ioloop.IOLoopKernelManager'

#  Default: ''
# c.MappingKernelManager.root_dir = ''

## Share a single zmq.Context to talk to all my kernels
#  See also: MultiKernelManager.shared_context
# c.MappingKernelManager.shared_context = True

## Message to print when allow_tracebacks is False, and an exception occurs
#  Default: 'An exception occurred at runtime, which is not shown due to security reasons.'
# c.MappingKernelManager.traceback_replacement_message = 'An exception occurred at runtime, which is not shown due to security reasons.'

#------------------------------------------------------------------------------
# AsyncMappingKernelManager(MappingKernelManager, AsyncMultiKernelManager) configuration
#------------------------------------------------------------------------------
## Whether to send tracebacks to clients on exceptions.
#  See also: MappingKernelManager.allow_tracebacks
# c.AsyncMappingKernelManager.allow_tracebacks = True

## White list of allowed kernel message types.
#  See also: MappingKernelManager.allowed_message_types
# c.AsyncMappingKernelManager.allowed_message_types = []

## Whether messages from kernels whose frontends have disconnected should be
#  buffered in-memory.
#  See also: MappingKernelManager.buffer_offline_messages
# c.AsyncMappingKernelManager.buffer_offline_messages = True

## Whether to consider culling kernels which are busy.
#  See also: MappingKernelManager.cull_busy
# c.AsyncMappingKernelManager.cull_busy = False

## Whether to consider culling kernels which have one or more connections.
#  See also: MappingKernelManager.cull_connected
# c.AsyncMappingKernelManager.cull_connected = False

## Timeout (in seconds) after which a kernel is considered idle and ready to be
#  culled.
#  See also: MappingKernelManager.cull_idle_timeout
# c.AsyncMappingKernelManager.cull_idle_timeout = 0

## The interval (in seconds) on which to check for idle kernels exceeding the
#  cull timeout value.
#  See also: MappingKernelManager.cull_interval
# c.AsyncMappingKernelManager.cull_interval = 300

## The name of the default kernel to start
#  See also: MultiKernelManager.default_kernel_name
# c.AsyncMappingKernelManager.default_kernel_name = 'python3'

## Timeout for giving up on a kernel (in seconds).
#  See also: MappingKernelManager.kernel_info_timeout
# c.AsyncMappingKernelManager.kernel_info_timeout = 60

## The kernel manager class.  This is configurable to allow
#  See also: AsyncMultiKernelManager.kernel_manager_class
# c.AsyncMappingKernelManager.kernel_manager_class = 'jupyter_client.ioloop.AsyncIOLoopKernelManager'

#  See also: MappingKernelManager.root_dir
# c.AsyncMappingKernelManager.root_dir = ''

## Share a single zmq.Context to talk to all my kernels
#  See also: MultiKernelManager.shared_context
# c.AsyncMappingKernelManager.shared_context = True

## Message to print when allow_tracebacks is False, and an exception occurs
#  See also: MappingKernelManager.traceback_replacement_message
# c.AsyncMappingKernelManager.traceback_replacement_message = 'An exception occurred at runtime, which is not shown due to security reasons.'

#------------------------------------------------------------------------------
# RemoteMappingKernelManager(AsyncMappingKernelManager) configuration
#------------------------------------------------------------------------------
## Extends the AsyncMappingKernelManager with support for managing remote kernels
#  via the process-proxy.

## Whether to send tracebacks to clients on exceptions.
#  See also: MappingKernelManager.allow_tracebacks
# c.RemoteMappingKernelManager.allow_tracebacks = True

## White list of allowed kernel message types.
#  See also: MappingKernelManager.allowed_message_types
# c.RemoteMappingKernelManager.allowed_message_types = []

## Whether messages from kernels whose frontends have disconnected should be
#  buffered in-memory.
#  See also: MappingKernelManager.buffer_offline_messages
# c.RemoteMappingKernelManager.buffer_offline_messages = True

## Whether to consider culling kernels which are busy.
#  See also: MappingKernelManager.cull_busy
# c.RemoteMappingKernelManager.cull_busy = False

## Whether to consider culling kernels which have one or more connections.
#  See also: MappingKernelManager.cull_connected
# c.RemoteMappingKernelManager.cull_connected = False

## Timeout (in seconds) after which a kernel is considered idle and ready to be
#  culled.
#  See also: MappingKernelManager.cull_idle_timeout
# c.RemoteMappingKernelManager.cull_idle_timeout = 0

## The interval (in seconds) on which to check for idle kernels exceeding the
#  cull timeout value.
#  See also: MappingKernelManager.cull_interval
# c.RemoteMappingKernelManager.cull_interval = 300

## The name of the default kernel to start
#  See also: MultiKernelManager.default_kernel_name
# c.RemoteMappingKernelManager.default_kernel_name = 'python3'

## Timeout for giving up on a kernel (in seconds).
#  See also: MappingKernelManager.kernel_info_timeout
# c.RemoteMappingKernelManager.kernel_info_timeout = 60

## The kernel manager class.  This is configurable to allow
#  See also: AsyncMultiKernelManager.kernel_manager_class
# c.RemoteMappingKernelManager.kernel_manager_class = 'jupyter_client.ioloop.AsyncIOLoopKernelManager'

#  See also: MappingKernelManager.root_dir
# c.RemoteMappingKernelManager.root_dir = ''

## Share a single zmq.Context to talk to all my kernels
#  See also: MultiKernelManager.shared_context
# c.RemoteMappingKernelManager.shared_context = True

## Message to print when allow_tracebacks is False, and an exception occurs
#  See also: MappingKernelManager.traceback_replacement_message
# c.RemoteMappingKernelManager.traceback_replacement_message = 'An exception occurred at runtime, which is not shown due to security reasons.'
