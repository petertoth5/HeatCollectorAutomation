#!/bin/bash

# Load credentials
if [ -f ~/.config/proxy/credentials ]; then
    source ~/.config/proxy/credentials
fi

# Launch Claude with environment variables
env \
  ANTHROPIC_BASE_URL="https://llm-gateway.ve42034x.automotive-wan.com" \
  ANTHROPIC_AUTH_TOKEN="gAAAAABputbef8i-eFDFSk9NaWzYD9xQjfujUh1nDluiMuRm21Z5y9K5BrpTdoC-IxL2CquFAifBvkYho_92jqNbMMB-rlVrP9P3mqdQIl4lpVueE5acAaHYfFwkf1kVTC0mi2onZNqRZa-6T-BLD9B6NfQi2KgGYA==" \
  NODE_TLS_REJECT_UNAUTHORIZED=0 \
  claude "$@"
