from ...base_exceptions import UTZError, ConfigurationError


class SerializerError(UTZError):
    """There was an error with the model"""
    pass


class SerializerConfigurationError(ConfigurationError):
    """There was an error with the model's configuration"""
    pass
