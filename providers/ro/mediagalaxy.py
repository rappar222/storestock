from providers.ro.altex import AltexProvider

class MediaGalaxyProvider(AltexProvider):
    store_id = "mediagalaxy_ro"
    store_name = "Media Galaxy"
    country_code = "RO"
    store_icon = "tv"
    brand_header = "mediagalaxy"

    def _sync_search(self, query: str):
        results = super()._sync_search(query)
        # Update URLs to mediagalaxy.ro domain
        for r in results:
            r.store_name = self.store_name
            r.store_icon = self.store_icon
            if "altex.ro" in r.product_url:
                r.product_url = r.product_url.replace("altex.ro", "mediagalaxy.ro")
        return results
