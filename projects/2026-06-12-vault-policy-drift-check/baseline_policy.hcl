path "secret/data/apps/payments/config" {
  capabilities = ["read"]
}

path "secret/metadata/apps/payments/*" {
  capabilities = ["read", "list"]
}

path "sys/health" {
  capabilities = ["read"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}
