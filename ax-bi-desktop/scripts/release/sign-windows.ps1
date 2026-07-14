<#
.SYNOPSIS
Signs Windows release artifacts with the DEFAI certificate in Azure Key Vault.

.DESCRIPTION
AzureSignTool performs the private-key operation inside Azure Key Vault. The
script then verifies each Authenticode signature and its signer thumbprint.
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string[]] $Path
)

$ErrorActionPreference = "Stop"

$requiredEnvironment = @(
  "AZURE_TENANT_ID",
  "AZURE_CLIENT_ID",
  "AZURE_CLIENT_SECRET",
  "AZURE_KEY_VAULT_URL",
  "AZURE_KEY_VAULT_CERTIFICATE",
  "WINDOWS_SIGNING_THUMBPRINT"
)

foreach ($name in $requiredEnvironment) {
  if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) {
    throw "Required environment variable $name is not set."
  }
}

$toolPath = Join-Path $env:USERPROFILE ".dotnet\tools\AzureSignTool.exe"
if (-not (Test-Path -LiteralPath $toolPath -PathType Leaf)) {
  throw "AzureSignTool was not found at $toolPath."
}

$resolvedPaths = @(
  foreach ($item in $Path) {
    (Resolve-Path -LiteralPath $item -ErrorAction Stop).Path
  }
)

if ($resolvedPaths.Count -eq 0) {
  throw "At least one Windows artifact is required."
}

& $toolPath sign `
  --azure-key-vault-url $env:AZURE_KEY_VAULT_URL `
  --azure-key-vault-client-id $env:AZURE_CLIENT_ID `
  --azure-key-vault-client-secret $env:AZURE_CLIENT_SECRET `
  --azure-key-vault-tenant-id $env:AZURE_TENANT_ID `
  --azure-key-vault-certificate $env:AZURE_KEY_VAULT_CERTIFICATE `
  --description "AX BI" `
  --description-url "https://github.com/defai-digital/ax-bi" `
  --file-digest sha256 `
  --timestamp-rfc3161 "http://timestamp.digicert.com" `
  --timestamp-digest sha256 `
  @resolvedPaths

if ($LASTEXITCODE -ne 0) {
  throw "AzureSignTool failed with exit code $LASTEXITCODE."
}

$expectedThumbprint = $env:WINDOWS_SIGNING_THUMBPRINT -replace "[^0-9A-Fa-f]", ""
foreach ($artifact in $resolvedPaths) {
  $signature = Get-AuthenticodeSignature -LiteralPath $artifact
  if ($signature.Status -ne "Valid") {
    throw "Authenticode verification failed for ${artifact}: $($signature.StatusMessage)"
  }

  $actualThumbprint = $signature.SignerCertificate.Thumbprint -replace "[^0-9A-Fa-f]", ""
  if ($actualThumbprint -ne $expectedThumbprint) {
    throw "Unexpected signing certificate for $artifact (thumbprint $actualThumbprint)."
  }

  Write-Host "Verified Authenticode signature: $artifact"
}
