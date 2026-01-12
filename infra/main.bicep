targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment used to generate a short unique hash for resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources.')
param location string

@description('Optional. Azure OpenAI endpoint to inject into the container app.')
param azureOpenAiEndpoint string = ''

@description('Optional. Azure OpenAI chat/reasoning deployment name.')
param azureOpenAiDeploymentName string = 'gpt-5-2'

@description('Optional. Azure OpenAI interactive (chat) deployment name.')
param azureOpenAiChatDeploymentName string = 'gpt-5-2-chat'

@description('Container image to deploy. Defaults to a placeholder until azd pushes the app image.')
param apiImageName string = ''

var abbrs = loadJsonContent('abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: '${abbrs.resourceGroup}${environmentName}'
  location: location
  tags: tags
}

module resources 'resources.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    location: location
    tags: tags
    resourceToken: resourceToken
    abbrs: abbrs
    azureOpenAiEndpoint: azureOpenAiEndpoint
    azureOpenAiDeploymentName: azureOpenAiDeploymentName
    azureOpenAiChatDeploymentName: azureOpenAiChatDeploymentName
    apiImageName: apiImageName
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.containerRegistryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = resources.outputs.containerRegistryName
output AZURE_COSMOS_ENDPOINT string = resources.outputs.cosmosDbEndpoint
output AZURE_AI_SEARCH_ENDPOINT string = resources.outputs.searchEndpoint
output SERVICE_API_ENDPOINT string = resources.outputs.apiEndpoint
output APPLICATIONINSIGHTS_CONNECTION_STRING string = resources.outputs.applicationInsightsConnectionString
