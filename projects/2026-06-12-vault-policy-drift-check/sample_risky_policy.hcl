path "secret/data/apps/payments/config" {
  capabilities = ["read", "update"]
}

path "secret/data/prod/*" {
  capabilities = ["read", "update", "delete"]
}

path "sys/*" {
  capabilities = ["read", "list", "sudo"]
}

path "auth/token/create" {
  capabilities = ["create", "update"]
}
