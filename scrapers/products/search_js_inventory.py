Here’s where we landed.

Quivrr is now using Azure SQL for live search, not local JSON. The backend API is returning product images and retailerLogoUrl, and the frontend is now rendering retailer logos and board images correctly.

Current state:

Area	Status
Live Azure SQL connection	Working
Product images in result cards	Working
Retailer logos in result cards	Working
Available stock only imported	Working
Retailer profiles enriched	78 profiles
Retailers with searchable inventory	~21 active
Backend deployment	Manual Azure sync required after Git push

Important command after backend pushes:

az webapp deployment source sync `
  --name quivrr-backend-api `
  --resource-group quivrr-production-rg

Next session should focus on retailer scrape coverage.

Priority next steps:

Audit current scraper output and find why only ~21 retailers have live inventory.
Separate retailers into groups:
Shopify working
WooCommerce working
blocked
wrong platform
no catalogue endpoint
needs custom scraper
Fix the active target builder so we are scraping all usable retailers from the 78 profile list.
Add missing large Australian retailers.
Improve scrape health reporting so each nightly run shows:
retailer name
platform
raw products found
surfboards accepted
available surfboards
fail reason
Then wire this into Azure nightly scheduling.

Key issue for next time:

We have 78 retailer profiles, but only about 21 retailers contributing searchable inventory.

The next technical target is not UI anymore. It is the scrape pipeline and retailer activation coverage.