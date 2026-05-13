# Quivrr Retailer Recon Report

Generated: 2026-05-14T01:26:34

This report identifies ecommerce platforms, likely protection layers, blocked endpoints and usable public product paths.

## Surf FX

URL: https://www.surffx.com.au

Status codes: 200, 400, 404

Platform signals: Salesforce Commerce Cloud, Shopify, WooCommerce, WordPress

CDN or WAF: Cloudflare, Cloudflare, Shopify Edge

Protection signals: Bot challenge, Cloudflare challenge, Geo restriction

Product signals: JSON products array, Product URL references, Retail product content, Surfboard keyword content, XML sitemap

Useful paths:
* /products
* /shop
* /search?q=surfboard
* /search?type=product&q=surfboard
* /
* /robots.txt
* /sitemap.xml
* /products.json?limit=250
* /collections/all/products.json?limit=250
* /collections/surfboards/products.json?limit=250

Recommended next step: Likely structured product feed available. Build or fix feed scraper first.

## Mundo Surf

URL: https://www.mundo-surf.com

Status codes: 200, 404

Platform signals: None found

CDN or WAF: Cloudflare

Protection signals: Cloudflare challenge

Product signals: None found

Useful paths:
* None found

Recommended next step: Protection or restriction detected. Use public sitemap, retailer feed, approved API, affiliate feed, or manual partnership path.

## Le BAO

URL: https://www.lebao.com.au

Status codes: None

Platform signals: None found

CDN or WAF: None found

Protection signals: None found

Product signals: None found

Useful paths:
* None found

Recommended next step: No reliable product path found. Needs manual inspection.

## Board Collectors

URL: https://www.boardcollectors.com

Status codes: None

Platform signals: None found

CDN or WAF: None found

Protection signals: None found

Product signals: None found

Useful paths:
* None found

Recommended next step: No reliable product path found. Needs manual inspection.

## Surfstitch

URL: https://www.surfstitch.com

Status codes: 200, 400, 404

Platform signals: Custom or unknown ecommerce, Shopify

CDN or WAF: Cloudflare, Cloudflare, Shopify Edge

Protection signals: Cloudflare challenge

Product signals: JSON products array, Product URL references, Retail product content, XML sitemap

Useful paths:
* /products.json?limit=250
* /collections/all/products.json?limit=250
* /collections/surfboards/products.json?limit=250
* /robots.txt
* /sitemap.xml

Recommended next step: Likely structured product feed available. Build or fix feed scraper first.

## Seaside Surf Shop

URL: https://www.seasidesurfshop.com.au

Status codes: None

Platform signals: None found

CDN or WAF: None found

Protection signals: None found

Product signals: None found

Useful paths:
* None found

Recommended next step: No reliable product path found. Needs manual inspection.

## 12 Board Store

URL: https://www.12boardstore.com.au

Status codes: None

Platform signals: None found

CDN or WAF: None found

Protection signals: None found

Product signals: None found

Useful paths:
* None found

Recommended next step: No reliable product path found. Needs manual inspection.

## Strapper Surf

URL: https://www.strapper.com.au

Status codes: 200, 404

Platform signals: WooCommerce, WordPress

CDN or WAF: None found

Protection signals: Bot challenge, Geo restriction

Product signals: Retail product content, Surfboard keyword content, XML sitemap

Useful paths:
* /
* /sitemap.xml

Recommended next step: WooCommerce detected. Build scraper around Store API, product sitemap, or product schema.

## Surf Dive n Ski

URL: https://www.sds.com.au

Status codes: None

Platform signals: None found

CDN or WAF: None found

Protection signals: None found

Product signals: None found

Useful paths:
* None found

Recommended next step: No reliable product path found. Needs manual inspection.

## City Beach

URL: https://www.citybeach.com

Status codes: None

Platform signals: None found

CDN or WAF: None found

Protection signals: None found

Product signals: None found

Useful paths:
* None found

Recommended next step: No reliable product path found. Needs manual inspection.

## Riders Lodge

URL: https://www.riderslodge.com.au

Status codes: None

Platform signals: None found

CDN or WAF: None found

Protection signals: None found

Product signals: None found

Useful paths:
* None found

Recommended next step: No reliable product path found. Needs manual inspection.

## Bennys Boardroom

URL: https://www.bennysboardroom.com.au

Status codes: None

Platform signals: None found

CDN or WAF: None found

Protection signals: None found

Product signals: None found

Useful paths:
* None found

Recommended next step: No reliable product path found. Needs manual inspection.

## Kirra Surf

URL: https://www.kirrasurf.com.au

Status codes: None

Platform signals: None found

CDN or WAF: None found

Protection signals: None found

Product signals: None found

Useful paths:
* None found

Recommended next step: No reliable product path found. Needs manual inspection.

## Boardcave

URL: https://www.boardcave.com.au

Status codes: 403

Platform signals: WooCommerce, WordPress

CDN or WAF: Cloudflare, Cloudflare, PerimeterX

Protection signals: Blocking or challenge status 403, Cloudflare challenge, Geo restriction, JavaScript required, PerimeterX challenge

Product signals: Surfboard keyword content

Useful paths:
* None found

Recommended next step: WooCommerce detected. Build scraper around Store API, product sitemap, or product schema.

## Trigger Bros

URL: https://www.triggerbrothers.com.au

Status codes: 403

Platform signals: WooCommerce, WordPress

CDN or WAF: Cloudflare

Protection signals: Blocking or challenge status 403, Cloudflare challenge, Geo restriction, JavaScript required

Product signals: Surfboard keyword content

Useful paths:
* None found

Recommended next step: WooCommerce detected. Build scraper around Store API, product sitemap, or product schema.

## Ocean and Earth

URL: https://www.oceanearthstore.com

Status codes: 200, 404

Platform signals: Shopify, WooCommerce, WordPress

CDN or WAF: Cloudflare, Shopify Edge

Protection signals: Bot challenge, Cloudflare challenge, Geo restriction

Product signals: Product URL references, Retail product content, Surfboard keyword content

Useful paths:
* /collections/all
* /collections/surfboard
* /products
* /api/products
* /shop
* /search?q=surfboard
* /search?type=product&q=surfboard
* /robots.txt

Recommended next step: Shopify detected, but common feeds may be blocked or unavailable. Test collection handles and sitemap product URLs.

## Momentum Surf

URL: https://www.momentumsurf.com.au

Status codes: None

Platform signals: None found

CDN or WAF: None found

Protection signals: None found

Product signals: None found

Useful paths:
* None found

Recommended next step: No reliable product path found. Needs manual inspection.

## SDS Surf

URL: https://www.sds.com.au

Status codes: 200, 400, 404

Platform signals: Custom or unknown ecommerce, Salesforce Commerce Cloud, Shopify, WooCommerce, WordPress

CDN or WAF: Cloudflare, Cloudflare, Shopify Edge

Protection signals: Bot challenge, Cloudflare challenge, Geo restriction, PerimeterX challenge

Product signals: JSON products array, Product URL references, Retail product content, Surfboard keyword content

Useful paths:
* /search?q=surfboard
* /search?type=product&q=surfboard
* /collections/all/products.json?limit=250
* /collections/surfboards/products.json?limit=250
* /collections/all
* /products
* /shop
* /search?q=surfboard
* /search?type=product&q=surfboard

Recommended next step: Likely structured product feed available. Build or fix feed scraper first.

## Onboard Store

URL: https://www.onboardstore.com.au

Status codes: 200, 400, 404

Platform signals: Custom or unknown ecommerce, Shopify, WooCommerce, WordPress

CDN or WAF: Cloudflare, Cloudflare, Shopify Edge

Protection signals: Cloudflare challenge

Product signals: JSON products array, Product URL references, Retail product content, Surfboard keyword content

Useful paths:
* /search?q=surfboard
* /search?type=product&q=surfboard
* /products.json?limit=250
* /collections/all/products.json?limit=250
* /collections/surfboards/products.json?limit=250
* /collections/all
* /products
* /shop
* /search?q=surfboard

Recommended next step: Likely structured product feed available. Build or fix feed scraper first.

## Natural Necessity

URL: https://www.naturalnecessity.com.au

Status codes: 200, 400, 404

Platform signals: Custom or unknown ecommerce, Shopify, WooCommerce, WordPress

CDN or WAF: Cloudflare, Cloudflare, Shopify Edge

Protection signals: Cloudflare challenge

Product signals: JSON products array, Product URL references, Retail product content, Surfboard keyword content, XML sitemap

Useful paths:
* /shop
* /search?q=surfboard
* /search?type=product&q=surfboard
* /
* /robots.txt
* /sitemap.xml
* /products.json?limit=250
* /shop
* /search?q=surfboard
* /search?type=product&q=surfboard

Recommended next step: Likely structured product feed available. Build or fix feed scraper first.

## Underground Surf

URL: https://www.undergroundsurf.com.au

Status codes: 200, 400, 404

Platform signals: Custom or unknown ecommerce, Shopify, WooCommerce, WordPress

CDN or WAF: Cloudflare, Cloudflare, AWS CloudFront, Shopify Edge, Cloudflare, Shopify Edge

Protection signals: Cloudflare challenge

Product signals: JSON products array, Product URL references, Retail product content, Surfboard keyword content, XML sitemap

Useful paths:
* /products.json?limit=250
* /collections/all/products.json?limit=250
* /collections/surfboards/products.json?limit=250
* /collections/all
* /products
* /shop
* /
* /robots.txt
* /sitemap.xml
* /products.json?limit=250

Recommended next step: Likely structured product feed available. Build or fix feed scraper first.

## Coastalwatch

URL: https://www.coastalwatch.com

Status codes: 403

Platform signals: None found

CDN or WAF: Cloudflare

Protection signals: Blocking or challenge status 403, Cloudflare challenge, Geo restriction, JavaScript required

Product signals: None found

Useful paths:
* None found

Recommended next step: Protection or restriction detected. Use public sitemap, retailer feed, approved API, affiliate feed, or manual partnership path.

## Sideways Surf

URL: https://www.sideways.com.au

Status codes: 200, 400, 404

Platform signals: Custom or unknown ecommerce, Shopify

CDN or WAF: Cloudflare, Cloudflare, Shopify Edge

Protection signals: Cloudflare challenge

Product signals: JSON products array, Product URL references, Retail product content, Surfboard keyword content, XML sitemap

Useful paths:
* /products.json?limit=250
* /collections/surfboards/products.json?limit=250
* /collections/all/products.json?limit=250
* /
* /robots.txt
* /sitemap.xml
* /collections/surfboards
* /collections/all
* /products.json?limit=250
* /

Recommended next step: Likely structured product feed available. Build or fix feed scraper first.

## Nth Degree

URL: https://www.nthdegree.com.au

Status codes: 200, 404

Platform signals: Squarespace

CDN or WAF: None found

Protection signals: Bot challenge

Product signals: Retail product content, Surfboard keyword content, XML sitemap

Useful paths:
* /search?type=product&q=surfboard
* /search?q=surfboard
* /
* /sitemap.xml

Recommended next step: Protection or restriction detected. Use public sitemap, retailer feed, approved API, affiliate feed, or manual partnership path.
