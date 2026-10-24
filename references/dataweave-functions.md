# DataWeave 2.x Common Functions & Patterns

## Core Functions

### String
| Function | Description |
|----------|-------------|
| `upper`, `lower` | Case conversion |
| `trim`, `ltrim`, `rtrim` | Whitespace removal |
| `splitBy`, `split` | Split string by regex/delimiter |
| `joinBy` | Join array with delimiter |
| `replace` | Regex replace |
| `match`, `matches` | Regex match/boolean |
| `substring`, `slice` | Extract substring |
| `sizeOf` | String/array length |
| `capitalize`, `uncapitalize` | First letter case |
| `camelize`, `dasherize`, `underscore` | Naming conventions |

### Array / List
| Function | Description |
|----------|-------------|
| `map` | Transform each element |
| `filter` | Keep elements matching predicate |
| `reduce` | Aggregate to single value |
| `flatMap` | Map + flatten |
| `distinctBy` | Unique by key |
| `groupBy` | Group by key |
| `orderBy` | Sort by key |
| `partition` | Split by predicate |
| `flatten` | Flatten nested arrays |
| `zip`, `unzip` | Pair/unpair arrays |
| `slice` | Sub-array |
| `find`, `findIndex` | First match |
| `every`, `some` | All/any match |

### Object
| Function | Description |
|----------|-------------|
| `pluck` | Map object to array of {key, value} |
| `keys`, `values` | Extract keys/values |
| `merge` | Merge objects |
| `mapObject` | Transform key-value pairs |
| `filterObject` | Filter by key/value |
| `remove` | Remove keys |
| `update` | Update value at key |

### Date/Time
| Function | Description |
|----------|-------------|
| `now()`, `today()` | Current datetime/date |
| `|>` (pipe) | Chain operations |
| `++` | Date + Period |
| `-` | Date - Date = Period |
| `format` | Format date as string |
| `fromString` | Parse string to date |
| `toMillis`, `fromMillis` | Epoch conversion |
| `withTimezone` | Change timezone |

### Type Coercion
```dw
payload as String
payload as Number
payload as Boolean
payload as Date {format: "yyyy-MM-dd"}
payload as :localdate
payload as :localtime
payload as :localdatetime
```

## Common Patterns

### Conditional
```dw
if (payload.status == "active") "live" else "inactive"

payload.status match {
  case "active" -> "live"
  case "pending" -> "waiting"
  else -> "unknown"
}
```

### Default Values
```dw
payload.name default "Unknown"
payload.age default 0
```

### Object Construction
```dw
{
  id: payload.id,
  fullName: payload.firstName ++ " " ++ payload.lastName,
  isAdult: payload.age >= 18,
  tags: payload.tags map (tag, index) -> { index: index, value: tag }
}
```

### Filter & Map
```dw
payload.users filter $.active map {
  id: $.id,
  name: $.name,
  email: $.email lower
}
```

### Group By
```dw
payload.orders groupBy $.customerId mapObject {
  (customerId): $
    map {
      orderId: $.id,
      total: $.amount
    }
    reduce (acc, item) -> acc + item.total
}
```

### Date Formatting
```dw
now() >> "yyyy-MM-dd'T'HH:mm:ss.SSSZ"
payload.createdAt >> "yyyy-MM-dd"
now() - |P1D| // subtract 1 day
```

### Mule Runtime Variables
```dw
vars.myVar
attributes.headers.Content-Type
attributes.queryParams.page
attributes.uriParams.id
error.errorMessage
```

### JSON/XML Handling
```dw
// Read JSON
read(payload, "application/json")

// Write XML
write(payload, "application/xml")

// Parse CSV
read(payload, "application/csv", {header: true})
```

## Mule-Specific Patterns

### Transform Message
```dw
%dw 2.0
output application/json
---
{
  requestId: attributes.headers["X-Request-ID"] default uuid(),
  timestamp: now() >> "yyyy-MM-dd'T'HH:mm:ss.SSSZ",
  payload: payload map (item, index) -> {
    index: index,
    data: item
  }
}
```

### Error Handling in DW
```dw
%dw 2.0
output application/json
---
try
  payload map (item) -> item.field
catch (e) -> {
  error: e.message,
  type: e.type
}
```

### Module Imports
```dw
%dw 2.0
import * from dw::core::Strings
import * from dw::core::Arrays
import * from dw::util::Values
output application/json
---
// use functions without namespace
```