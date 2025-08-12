#!/usr/bin/env python3
"""
Hue MCP Server Setup Script

This script discovers Philips Hue bridges on the network and helps set up authentication.
It will generate a .env file with the bridge IP and username needed for the server.
"""

import asyncio
import json
import socket
import sys
from typing import Dict, List, Optional

import httpx


class HueBridgeDiscovery:
    """Discovers Philips Hue bridges on the local network."""

    @staticmethod
    async def discover_via_nupnp() -> List[Dict[str, str]]:
        """Discover bridges using Philips' N-UPnP service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://discovery.meethue.com/")
                response.raise_for_status()
                bridges = response.json()
                print(f"🔍 Found {len(bridges)} bridge(s) via N-UPnP service")
                return bridges
        except Exception as e:
            print(f"❌ N-UPnP discovery failed: {e}")
            return []

    @staticmethod
    async def discover_via_mdns() -> List[Dict[str, str]]:
        """Discover bridges using mDNS/Bonjour (fallback method)."""
        bridges = []
        try:
            # Simple network scan for bridges on common subnets
            import ipaddress
            
            # Get local IP to determine subnet
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
            
            print(f"🔍 Scanning network {network} for Hue bridges...")
            
            async def check_ip(ip_str: str) -> Optional[Dict[str, str]]:
                try:
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        response = await client.get(f"http://{ip_str}/api/config")
                        data = response.json()
                        
                        # Check if this looks like a Hue bridge
                        if "bridgeid" in data and "name" in data:
                            return {"internalipaddress": ip_str, "id": data["bridgeid"]}
                except:
                    pass
                return None
            
            # Check a subset of IPs to avoid too many requests
            tasks = []
            for ip in list(network.hosts())[:50]:  # Check first 50 IPs
                tasks.append(check_ip(str(ip)))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            bridges = [r for r in results if isinstance(r, dict)]
            
            print(f"🔍 Found {len(bridges)} bridge(s) via network scan")
            return bridges
            
        except Exception as e:
            print(f"❌ mDNS/network discovery failed: {e}")
            return []

    @classmethod
    async def discover_bridges(cls) -> List[Dict[str, str]]:
        """Discover bridges using multiple methods."""
        print("🔍 Discovering Hue bridges...")
        
        # Try N-UPnP first (more reliable)
        bridges = await cls.discover_via_nupnp()
        
        # If no bridges found, try network scan
        if not bridges:
            bridges = await cls.discover_via_mdns()
        
        return bridges


class HueBridgeAuth:
    """Handles authentication with Hue bridge."""
    
    def __init__(self, bridge_ip: str):
        self.bridge_ip = bridge_ip
        self.base_url = f"http://{bridge_ip}/api"
    
    async def create_user(self, app_name: str = "hue_mcp_server") -> Optional[str]:
        """Create a new user on the bridge."""
        data = {"devicetype": app_name}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.base_url, json=data)
                response.raise_for_status()
                result = response.json()
                
                if isinstance(result, list) and result:
                    if "success" in result[0]:
                        username = result[0]["success"]["username"]
                        print(f"✅ Successfully created user: {username}")
                        return username
                    elif "error" in result[0]:
                        error = result[0]["error"]
                        if error.get("type") == 101:
                            print("❌ Link button not pressed. Please press the link button on your Hue bridge.")
                        else:
                            print(f"❌ Error creating user: {error.get('description', 'Unknown error')}")
                        return None
                
                print(f"❌ Unexpected response: {result}")
                return None
                
            except Exception as e:
                print(f"❌ Failed to create user: {e}")
                return None
    
    async def test_user(self, username: str) -> bool:
        """Test if the username works with the bridge."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/{username}/config")
                response.raise_for_status()
                data = response.json()
                
                # Check if we got bridge config (not an error)
                if isinstance(data, dict) and "bridgeid" in data:
                    return True
                    
                return False
                
        except Exception:
            return False


async def interactive_setup():
    """Interactive setup process."""
    print("🌈 Hue MCP Server Setup")
    print("=" * 40)
    
    # Step 1: Discover bridges
    discovery = HueBridgeDiscovery()
    bridges = await discovery.discover_bridges()
    
    if not bridges:
        print("❌ No Hue bridges found on the network.")
        print("   Please ensure your bridge is connected and try again.")
        return False
    
    # Step 2: Select bridge
    if len(bridges) == 1:
        bridge = bridges[0]
        bridge_ip = bridge["internalipaddress"]
        print(f"📍 Using bridge at {bridge_ip} (ID: {bridge.get('id', 'Unknown')})")
    else:
        print("🔍 Multiple bridges found:")
        for i, bridge in enumerate(bridges):
            print(f"  {i + 1}. {bridge['internalipaddress']} (ID: {bridge.get('id', 'Unknown')})")
        
        while True:
            try:
                choice = input("Select bridge (1-{}): ".format(len(bridges)))
                idx = int(choice) - 1
                if 0 <= idx < len(bridges):
                    bridge = bridges[idx]
                    bridge_ip = bridge["internalipaddress"]
                    break
                else:
                    print("❌ Invalid selection. Please try again.")
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Setup cancelled.")
                return False
    
    # Step 3: Authentication
    auth = HueBridgeAuth(bridge_ip)
    
    print(f"\n🔗 Connecting to bridge at {bridge_ip}")
    print("🔴 Please press the LINK BUTTON on your Hue bridge now!")
    print("   You have 30 seconds after pressing the button...")
    
    input("Press ENTER when you have pressed the link button: ")
    
    # Try to create user for up to 30 seconds
    print("🔄 Attempting to authenticate...")
    
    username = None
    for attempt in range(6):  # 6 attempts over 30 seconds
        username = await auth.create_user()
        if username:
            break
        
        if attempt < 5:
            print(f"   Retrying in 5 seconds... (attempt {attempt + 1}/6)")
            await asyncio.sleep(5)
    
    if not username:
        print("❌ Failed to authenticate with the bridge.")
        print("   Please make sure you pressed the link button and try again.")
        return False
    
    # Step 4: Test authentication
    print("🧪 Testing authentication...")
    if await auth.test_user(username):
        print("✅ Authentication successful!")
    else:
        print("❌ Authentication test failed.")
        return False
    
    # Step 5: Create .env file
    env_content = f"""# Hue MCP Server Configuration

# Philips Hue Bridge Settings
HUE_BRIDGE_IP={bridge_ip}
HUE_USERNAME={username}

# Logging Configuration
LOG_LEVEL=INFO

# HTTP Client Settings
HUE_TIMEOUT_CONNECT=5.0
HUE_TIMEOUT_READ=10.0
HUE_MAX_CONNECTIONS=10
HUE_MAX_KEEPALIVE=5

# Rate Limiting Settings
HUE_LIGHT_RATE_LIMIT=10
HUE_GROUP_RATE_LIMIT=1.0
"""
    
    try:
        with open(".env", "w") as f:
            f.write(env_content)
        print("✅ Created .env file with your bridge configuration")
        print("🚀 Setup complete! You can now run the Hue MCP server.")
        return True
    except Exception as e:
        print(f"❌ Failed to write .env file: {e}")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hue MCP Server Setup Script")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Test bridge discovery without creating .env file"
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Only discover bridges, don't authenticate"
    )
    
    args = parser.parse_args()
    
    try:
        if args.dry_run or args.discover_only:
            success = asyncio.run(dry_run_discovery())
        else:
            success = asyncio.run(interactive_setup())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


async def dry_run_discovery():
    """Dry run - just discover bridges."""
    print("🌈 Hue MCP Server Setup (Discovery Only)")
    print("=" * 40)
    
    discovery = HueBridgeDiscovery()
    bridges = await discovery.discover_bridges()
    
    if not bridges:
        print("❌ No Hue bridges found on the network.")
        return False
    
    print("✅ Bridge discovery successful!")
    for i, bridge in enumerate(bridges):
        print(f"  Bridge {i + 1}: {bridge['internalipaddress']} (ID: {bridge.get('id', 'Unknown')})")
    
    print("\n💡 To complete setup, run: python setup.py")
    return True


if __name__ == "__main__":
    main()