# Staging Environment Variables

environment        = "staging"
cloud_provider     = "aws"
region             = "us-east-1"
app_name           = "my-api"
db_instance_class  = "db.t3.small"
redis_node_type    = "cache.t3.small"
k8s_node_count     = 3
k8s_node_size      = "t3.medium"
single_nat_gateway = true  # Cost optimization for staging
