# Start building and personal AI connections

The website entry point has no email/password form. **Start building** creates a private workspace and initial project, then stores a random session in an HttpOnly, SameSite Strict cookie. HTTPS sessions are Secure. The browser session lasts up to one year. Returning in the same browser resumes it; clearing site data or changing devices does not recover that workspace automatically.

Existing legacy accounts, data and programmatic authentication routes are retained for compatibility. They are not shown as login/signup flows in the new interface. Workspace isolation still requires authenticated sessions internally. Anonymous access to private project data remains denied.

## Profile & settings

1. Open Profile & settings from the sidebar or the Go to page menu.
2. Choose a provider and the API protocol supported by the exact model.
3. Enter the exact model ID and your own API key. Add a recognizable connection name.
4. Select whether this becomes the active connection, then save. Saving invokes no model.
5. Test connection explicitly to send a small real inference request that checks an exact tool-call argument. This can consume credit. It is not a complete autonomous-team evaluation.
6. Add an optional personal LangSearch or Tavily key for live web research. When both are saved, LangSearch is selected.

Supported provider configurations: Groq, xAI/Grok, Anthropic, Google Gemini, OpenAI, DeepSeek, OpenCode Console/Zen, OpenRouter, Mistral, Together and Fireworks. Compatibility depends on the model's actual tool support and selected API protocol. No claim that every provider/model combination passed live inference is made. The current tests verify routing/client configuration without substituting provider responses.

OpenAI supports Responses or Chat Completions. OpenCode uses its current provider-specific inference routes: OpenAI chat or Responses, or Anthropic Messages. Its native Google routes are not implemented by the OpenCode adapter; use the direct Gemini connection for Gemini's OpenAI-compatible interface. See [OpenCode's model table](https://opencode.ai/v2/docs/console/models/), [OpenAI API documentation](https://developers.openai.com/api/reference/overview) and [Gemini integration documentation](https://ai.google.dev/gemini-api/docs/partner-integration).

Agents, Mem0 extraction and admission use the active personal connection by default. Advanced admission settings can select another connection owned by the same user and workspace. A selected Groq Safeguard model uses the existing Safeguard decision path. Other selected policy models must return strictly validated decisions. Neither path is proof of truth or a calibrated probability.

## Credential boundaries

- Personal connections and search keys are scoped to both user and tenant. Another visitor cannot read, activate, test or delete them.
- Fernet encrypts stored keys. Responses expose configuration and test status, never the stored plaintext or ciphertext. Validation errors omit submitted values so malformed bodies cannot echo secrets.
- The runtime uses task-local provider settings. API requests, agent tasks, ingestion jobs and Mem0 instances do not inherit the operator's provider keys. Fixed provider endpoints avoid accepting arbitrary visitor-supplied URLs.
- The browser holds keys only while the user enters them. Saving clears the key field; keys are not written into localStorage, task prompts or sandbox environment variables.
- The server operator controls the encryption secret. This is server-side encryption, not end-to-end encryption against that operator.
- `data/collective/secrets/provider.key` is the default encryption secret. A deployment may instead supply `PROVIDER_ENCRYPTION_KEY`. Preserve the secret with backups and migrations; changing it without re-encryption makes existing stored keys unreadable.
- Removing a connection removes the stored copy and prevents its selection by new operations. Running operations may already hold a loaded client/key. Stop active work before rotation and revoke a compromised key with the provider itself.
- LangSearch reservations are keyed by the credential hash, with a 1,000-request daily cap per credential across local processes.

Free hosting does not provide unlimited free inference. Quota and billing remain with each visitor's provider account. No substitute model or successful response is returned on failure.
