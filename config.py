from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    # Tells it to automatically load values from .env file. 
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')
    
    database_url:str 
    
    secret_key: SecretStr  # It will catch all the Uppercase variable
    algorithm: str = 'HS256' 
    access_token_expire_minutes: int = 30
    
    max_upload_size_bytes: int = 5 * 1024 * 1024 # maximum file size for 5mb
    
    posts_per_page:int = 10
    
    reset_token_expire_minutes: int = 60 
    
    mail_server: str = "localhost" # SMTP server host name 
    mail_port: int = 587
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "noreply@example.com"
    mail_use_tls: bool = True

    frontend_url: str = "http://localhost:8000"
    
    # S3 Configuration
    s3_bucket_name: str
    s3_region: str = "ap-southeast-2"  # values set here are just default values if the true values from the .env file does not exist
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_endpoint_url: str | None = None
        
# It will first look at the variable from system environment
# If they are not exist in the system env, hen will look through the .env file
# If neither of them exist, then it will use the default value we set in the class (in our case like secret_key would be needed as there is no default value)
    

settings = Settings() # type: ignore[call-arg] # Loaded from .env file