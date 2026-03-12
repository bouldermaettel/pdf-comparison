// Azure Container Apps deployment for PDF Comparison Utility
// Deploy: az deployment group create -g <rg> --template-file infra/main.bicep --parameters infra/parameters.json

@description('Base name for resources and the container app.')
param appName string = 'pdf-comparison'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Container image for the app (for example ghcr.io/org/pdf-comparison:latest or myacr.azurecr.io/pdf-comparison:latest).')
param containerImage string

@description('Optional private registry server, for example myacr.azurecr.io. Leave empty for public images.')
param registryServer string = ''

@description('Optional private registry username. Leave empty for public images.')
param registryUsername string = ''

@description('Optional private registry password. Leave empty for public images.')
@secure()
param registryPassword string = ''

@description('Container App CPU cores as string (e.g. 0.5, 1.0, 2.0).')
param cpuCores string = '1.0'

@description('Container App memory size (e.g. 1Gi, 2Gi, 4Gi).')
param memorySize string = '2Gi'

@description('Minimum replicas.')
param minReplicas int = 1

@description('Maximum replicas.')
param maxReplicas int = 2

var useRegistryCreds = !empty(registryServer) && !empty(registryUsername) && !empty(registryPassword)

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${appName}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${appName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: useRegistryCreds
        ? [
            {
              server: registryServer
              username: registryUsername
              passwordSecretRef: 'registry-password'
            }
          ]
        : []
      secrets: useRegistryCreds
        ? [
            {
              name: 'registry-password'
              value: registryPassword
            }
          ]
        : []
    }
    template: {
      containers: [
        {
          name: appName
          image: containerImage
          resources: {
            cpu: json(cpuCores)
            memory: memorySize
          }
          env: [
            {
              name: 'HOST'
              value: '0.0.0.0'
            }
            {
              name: 'PORT'
              value: '8000'
            }
          ]
          probes: [
            {
              type: 'Startup'
              httpGet: {
                path: '/api/health'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 5
              failureThreshold: 30
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/health'
                port: 8000
              }
              initialDelaySeconds: 15
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/api/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

output appUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output environmentName string = containerEnv.name
