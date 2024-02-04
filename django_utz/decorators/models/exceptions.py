from ...base_exceptions import UTZError, ConfigurationError


class ModelError(UTZError):
    """There was an error with the model"""
    pass


class ModelConfigurationError(ConfigurationError):
    """There was an error with the model's configuration"""
    pass
