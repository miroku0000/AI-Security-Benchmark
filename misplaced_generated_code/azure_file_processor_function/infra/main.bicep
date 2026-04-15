param functionPrincipalId string
param storageAccountName string
param cosmosAccountName string
param eventGridTopicName string

var storageBlobDataContributor = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '17d1049b-9a7f-48fa-8e49-c23ffd4620e4')
var cosmosDbAccountContributor = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a1-ab88-20be8b89f32fd')
var eventGridDataSender = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4d1568f4-9d07-4d7e-8d42-9d0e6d0d0e0d')

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosAccountName
}

resource eventGridTopic 'Microsoft.EventGrid/topics@2022-06-15' existing = {
  name: eventGridTopicName
}

resource raStorage 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionPrincipalId, storageBlobDataContributor)
  scope: storageAccount
  properties: {
    roleDefinitionId: storageBlobDataContributor
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource raCosmos 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cosmosAccount.id, functionPrincipalId, cosmosDbAccountContributor)
  scope: cosmosAccount
  properties: {
    roleDefinitionId: cosmosDbAccountContributor
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource raEventGrid 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(eventGridTopic.id, functionPrincipalId, eventGridDataSender)
  scope: eventGridTopic
  properties: {
    roleDefinitionId: eventGridDataSender
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
  }
}
