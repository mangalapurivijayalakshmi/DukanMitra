import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from asgiref.sync import sync_to_async
from mcp.server.fastmcp import FastMCP
from agent_api import tools

mcp = FastMCP("DukanMitra")


@mcp.tool()
async def get_stock(product_name: str) -> dict:
    """Check current stock of a product. Accepts Telugu or English name."""
    return await sync_to_async(tools.get_stock)(product_name)


@mcp.tool()
async def low_stock_items() -> list:
    """List products whose stock is below the reorder limit."""
    return await sync_to_async(tools.low_stock_items)()


@mcp.tool()
async def today_sales() -> dict:
    """Get today's total sales amount and number of sales."""
    return await sync_to_async(tools.today_sales)()


@mcp.tool()
async def pending_credit() -> list:
    """List customers who owe money (udhar), highest first."""
    return await sync_to_async(tools.pending_credit)()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")