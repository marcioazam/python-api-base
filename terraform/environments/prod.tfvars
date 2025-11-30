# Production Environment Variables

environment        = "prod"
cloud_provider     = "aws"
region             = "us-east-1"
app_name           = "my-api"
db_instance_class  = "db.r6g.large"
redis_node_type    = "cache.r6g.large"
k8s_node_count     = 5
k8s_node_size      = "t3.xlarge"
single_nat_gateway = false  # High availability for prod
