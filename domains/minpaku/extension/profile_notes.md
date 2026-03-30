# Minpaku Extension — AGENT.md Profile Notes

Add this section to AGENT.md when deploying with the `minpaku` extension.

---

## Minpaku Extension — Live Property and Booking Data

This deployment has access to live Minpaku vacation rental data via tool calls. The following tools are available:

### Available Tools

| Tool | When to use |
|---|---|
| `list_properties` | Operator asks "what properties do we have?", "show me all properties", or needs an overview |
| `search_properties` | Operator mentions a property by name or reference (e.g. "the Shinjuku apartment") |
| `get_bookings_by_property` | Operator asks about bookings, occupancy, or reservations for a specific property |

### Usage Guidelines

- **Call tools proactively** when the operator's question clearly requires live data. Do not ask "shall I look that up?" — just call the tool and present the result.
- **Present results clearly**: summarise key facts (property count, booking dates, guest names) rather than dumping raw JSON.
- **Handle errors gracefully**: if a tool returns an error (e.g. API not configured), explain simply: "The Minpaku API isn't configured — set MINPAKU_API_URL and MINPAKU_API_KEY in .env."
- **Combine with committed context**: cross-reference live booking data with contract terms stored in committed context where relevant.

### Example interactions

```
Operator: How many properties do we have?
→ Call list_properties, summarise count and names.

Operator: Show me bookings for the Osaka property.
→ Call search_properties("Osaka"), get the property ID, then call get_bookings_by_property.

Operator: Is unit 3B booked next month?
→ Call search_properties("3B") to find the property ID, then get_bookings_by_property.
```

### Environment requirements

```
MINPAKU_API_URL=https://your-minpaku-instance.com
MINPAKU_API_KEY=your_api_key_here
```

Set these in `.env` in the simply-connect project root before starting a session.
