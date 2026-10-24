# Mule XML Namespaces & Common Elements

## Core Namespaces

| Prefix | Namespace URI | Purpose |
|--------|---------------|---------|
| `mule` | `http://www.mulesoft.org/schema/mule/core` | Core Mule elements (flow, sub-flow, component) |
| `http` | `http://www.mulesoft.org/schema/mule/http` | HTTP listener, request, response |
| `ee` | `http://www.mulesoft.org/schema/mule/ee/core` | DataWeave, transform, message |
| `api-gateway` | `http://www.mulesoft.org/schema/mule/api-gateway` | Autodiscovery, policies |
| `apikit` | `http://www.mulesoft.org/schema/mule/apikit` | REST router from RAML/OAS |
| `db` | `http://www.mulesoft.org/schema/mule/db` | Database operations |
| `vm` | `http://www.mulesoft.org/schema/mule/vm` | VM queues (async) |
| `jms` | `http://www.mulesoft.org/schema/mule/jms` | JMS messaging |
| `salesforce` | `http://www.mulesoft.org/schema/mule/salesforce` | Salesforce connector |
| `sftp` | `http://www.mulesoft.org/schema/mule/sftp` | SFTP operations |
| `ftp` | `http://www.mulesoft.org/schema/mule/ftp` | FTP operations |
| `file` | `http://www.mulesoft.org/schema/mule/file` | File operations |
| `email` | `http://www.mulesoft.org/schema/mule/email` | Email (SMTP/IMAP) |
| `scheduler` | `http://www.mulesoft.org/schema/mule/scheduler` | Cron/quartz schedulers |
| `ws` | `http://www.mulesoft.org/schema/mule/ws` | Web Services (SOAP) |
| `validation` | `http://www.mulesoft.org/schema/mule/validation` | Schema validation |
| `secure-property` | `http://www.mulesoft.org/schema/mule/secure-property` | Encrypted properties |

## Common Elements

### Flow & Sub-Flow
```xml
<flow name="myFlow" >
  <http:listener config-ref="HTTP_Listener_config" path="/api/resource"/>
  <ee:transform>
    <ee:message>
      <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{ message: "Hello" }]]></ee:set-payload>
    </ee:message>
  </ee:transform>
</flow>

<sub-flow name="mySubFlow">
  <!-- reusable logic -->
</sub-flow>
```

### HTTP Listener
```xml
<http:listener-config name="HTTP_Listener_config" >
  <http:listener-connection host="0.0.0.0" port="8081" />
</http:listener-config>

<http:listener config-ref="HTTP_Listener_config" path="/users" method="GET" />
```

### APIkit Router
```xml
<apikit:config name="apiConfig" raml="api.raml" consoleEnabled="true" />

<flow name="api-main">
  <http:listener config-ref="HTTP_Listener_config" path="/api/*" />
  <apikit:router config-ref="apiConfig" />
</flow>
```

### Scheduler (Cron/Quartz)
```xml
<scheduler:config name="Scheduler_Config" >
  <scheduler:trigger-config>
    <scheduler:cron-trigger expression="0 0/5 * * * ?" />
  </scheduler:trigger-config>
</scheduler:config>

<flow name="scheduledFlow">
  <scheduler:trigger config-ref="Scheduler_Config" />
  <!-- flow logic -->
</flow>
```

### Database Config
```xml
<db:config name="Database_Config" >
  <db:generic-connection url="jdbc:mysql://localhost:3306/db" driverClassName="com.mysql.cj.jdbc.Driver" >
    <db:parameter key="user" value="${db.user}" />
    <db:parameter key="password" value="${db.password}" />
  </db:generic-connection>
</db:config>

<db:select config-ref="Database_Config" >
  <db:sql>SELECT * FROM users</db:sql>
</db:select>
```

### VM Queue
```xml
<vm:config name="VM_Config" >
  <vm:queues>
    <vm:queue queueName="myQueue" />
  </vm:queues>
</vm:config>

<vm:publish config-ref="VM_Config" queueName="myQueue" />
<vm:listener config-ref="VM_Config" queueName="myQueue" />
```

### Error Handling
```xml
<error-handler name="Global_Error_Handler" >
  <on-error-continue type="HTTP:NOT_FOUND" >
    <logger level="ERROR" message="Not found: #[error.description]" />
    <ee:transform>
      <ee:message>
        <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{ error: "Not found" }]]></ee:set-payload>
      </ee:message>
    </ee:transform>
  </on-error-continue>
  <on-error-continue >
    <logger level="ERROR" message="Error: #[error.description]" />
  </on-error-continue>
</error-handler>
```

### API Gateway Autodiscovery
```xml
<api-gateway:autodiscovery config-ref="API_Gateway_Config" apiId="${api.id}" flowRef="api-main" />

<api-gateway:config name="API_Gateway_Config" >
  <api-gateway:client-credentials-connection clientId="${client.id}" clientSecret="${client.secret}" />
</api-gateway:config>
```

### Property Placeholders
```xml
<configuration-properties file="${env}.yaml" />

<http:listener-config name="HTTP_Listener_config" >
  <http:listener-connection host="${http.host}" port="${http.port}" />
</http:listener-config>
```