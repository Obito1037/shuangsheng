from __future__ import annotations

from app.integrations.registry import ProviderRegistry, create_provider_registry


def get_provider_registry() -> ProviderRegistry:
    return create_provider_registry()

