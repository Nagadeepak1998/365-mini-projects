output "service_url" {
  description = "Public HTTPS endpoint for the service"
  value       = "https://api.example.com"
}

output "db_password" {
  description = "Database password for bootstrap testing only"
  value       = "super-secret"
  sensitive   = true
}

output "cluster_name" {
  description = "Primary Kubernetes cluster name"
  value       = "prod-cluster"
}
