# Failed Selenium/Chrome Attempts - Archive

This directory contains components from failed attempts to run Selenium + Chrome in Google Cloud Run.

## What's Here

- `Dockerfile.akc` - Docker configuration with Chrome installation (failed)
- `akc_selenium_scraper.py` - Selenium-based scraper (Chrome connection issues)
- `akc_file_scraper.py` - Earlier undetected-chromedriver attempt
- `requirements.akc.optimized.txt` - Dependencies for Selenium approach

## Why They Failed

**Root Issue**: Chrome browser doesn't work reliably in Cloud Run's sandboxed environment
- DevToolsActivePort file doesn't exist errors
- Connection timeouts to Chrome instances
- Resource constraints in containerized environment

**Attempts Made**: v1-v6 with various Chrome flags and configurations
- `--no-sandbox`, `--disable-dev-shm-usage`, `--headless=new`
- Regular Selenium vs undetected-chromedriver
- Memory allocation increases (2Gi, 4Gi)
- Different Chrome installation methods

**Conclusion**: Selenium + Chrome is not viable for Cloud Run deployments

## What We Learned

1. **Local scraping works perfectly** - BeautifulSoup + requests is reliable
2. **Cloud Run is great for APIs** - not for browser automation
3. **Flask job management system** - this part worked well and is reusable
4. **Monitoring infrastructure** - scripts and endpoints are solid

## Alternative Approaches (Not Implemented)

- Use ScrapingBee or Browserless.io cloud services
- Deploy to VM instead of Cloud Run
- Use Playwright with lighter resource footprint
- Find undocumented APIs instead of scraping