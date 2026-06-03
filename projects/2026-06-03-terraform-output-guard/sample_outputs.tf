output "service_url" {
  value = "https://api.example.com"
}

output "db_password" {
  description = "Database password for bootstrap testing only"
  value       = "super-secret"
}

output "cluster_name" {
  description = "Primary Kubernetes cluster name"
  value       = "prod-cluster"
}
