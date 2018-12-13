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

    def detect(self, identity, request):
        """Assign base groups to user identity
           based on request origin.

        :param str identity: User identity
        :param str request: Flask request object
        """
        self.logger.debug("Origin detection with request '%s'" % request)
        groups = []
        if 'host' in self.config:
            for group, expr in self.config['host'].items():
                if expr.match(request.host):
                    groups.append(group)
        self.logger.debug("Assigned groups: %s" % groups)
        if identity is None:
            identity = {'username': None}
        if len(groups) > 0:
            identity['group'] = groups[0]
        else:
            identity['group'] = '_public_'
        self.logger.info("identity: %s" % identity)
        return identity
