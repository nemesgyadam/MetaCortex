# How to Get Wolt API Tokens

## Authentication Process

Follow these steps to obtain the authentication tokens needed for the Wolt MCP server:

1. Open [Wolt.com](https://wolt.com) in your browser
2. Press `F12` to open developer tools
3. Navigate to the **Network** tab in developer tools
4. Log in to your Wolt account
5. In the network tab, use the search field to filter for `access_token`
6. Look for XHR type requests in the filtered results
7. Click on a relevant request and examine the response
8. In the response, look for:
   - `access_token` - This is your AUTH_TOKEN
   - `session_id` - This is your SESSION_ID

## Running the MCP Server

Use the obtained tokens when starting the Wolt MCP server:

```bash
python wolt.py --auth-token YOUR_ACCESS_TOKEN --session-id YOUR_SESSION_ID
```

**Note:** Tokens expire after some time, so you may need to repeat this process if you encounter authentication errors.