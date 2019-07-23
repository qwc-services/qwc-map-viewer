import re


class OriginDetector:
    """Request origin detection

    Assigns base groups to user identity
    based on request origin.
    """

    def __init__(self, logger, config):
        """Constructor

        :param Logger logger: Application logger
        :param obj config: Rules configuration
        """
        self.logger = logger
        self.config = config
        if 'host' in self.config:
            for group, expr in self.config['host'].items():
                self.config['host'][group] = re.compile(expr)
        if 'ip' in self.config:
            for group, expr in self.config['ip'].items():
                self.config['ip'][group] = re.compile(expr)

    def detect(self, identity, request):
        """Assign base groups to user identity
           based on request origin.

        :param str identity: User identity
        :param str request: Flask request object
        """
        self.logger.debug("Origin detection with request '%s'" % request)

        groups = []

        if 'host' in self.config:
            self.logger.debug("Checking host: %s" % request.host)
            for group, expr in self.config['host'].items():
                if expr.match(request.host):
                    groups.append(group)

        if 'ip' in self.config:
            try:
                self.logger.debug(
                    "Checking access_route: %s" % request.access_route
                )
                # get client IP
                remote_ip = request.access_route[0]
            except ValueError:
                remote_ip = ""
            for group, expr in self.config['ip'].items():
                if expr.match(remote_ip):
                    groups.append(group)

        self.logger.debug("Assigned groups: %s" % groups)

        username = None
        if identity:
            if isinstance(identity, dict):
                username = identity.get('username')
                # NOTE: ignore group from identity
            else:
                # identity is username
                username = identity

        group = None
        if groups:
            group = groups[0]
        else:
            group = '_public_'

        identity = {
            'username': username,
            'group': group
        }
        self.logger.info("identity: %s" % identity)
        return identity
