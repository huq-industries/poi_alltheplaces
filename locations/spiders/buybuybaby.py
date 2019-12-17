# -*- coding: utf-8 -*-
import json
import scrapy
import re

from locations.items import GeojsonPointItem


class BuyBuyBabySpider(scrapy.Spider):
    name = "buybuybaby"
    brand = "Buy Buy Baby"
    allowed_domains = ["buybuybaby.com"]
    start_urls = (
        'https://stores.buybuybaby.com/',
    )

    def store_hours(self, store_hours):
        day_groups = []
        this_day_group = None
        for day_info in store_hours:
            day = day_info['day'][:2].title()

            hour_intervals = []
            for interval in day_info['intervals']:
                f_time = str(interval['start']).zfill(4)
                t_time = str(interval['end']).zfill(4)
                hour_intervals.append('{}:{}-{}:{}'.format(
                    f_time[0:2],
                    f_time[2:4],
                    t_time[0:2],
                    t_time[2:4],
                ))
            hours = ','.join(hour_intervals)

            if not this_day_group:
                this_day_group = {
                    'from_day': day,
                    'to_day': day,
                    'hours': hours
                }
            elif this_day_group['hours'] != hours:
                day_groups.append(this_day_group)
                this_day_group = {
                    'from_day': day,
                    'to_day': day,
                    'hours': hours
                }
            elif this_day_group['hours'] == hours:
                this_day_group['to_day'] = day

        day_groups.append(this_day_group)

        opening_hours = ""
        if len(day_groups) == 1 and day_groups[0]['hours'] in ('00:00-23:59', '00:00-00:00'):
            opening_hours = '24/7'
        else:
            for day_group in day_groups:
                if day_group['from_day'] == day_group['to_day']:
                    opening_hours += '{from_day} {hours}; '.format(**day_group)
                elif day_group['from_day'] == 'Su' and day_group['to_day'] == 'Sa':
                    opening_hours += '{hours}; '.format(**day_group)
                else:
                    opening_hours += '{from_day}-{to_day} {hours}; '.format(**day_group)
            opening_hours = opening_hours[:-2]

        return opening_hours

    def parse_store(self, response):
        if "bedbathandbeyond" in response.url:
            return
        ref = re.search(r".com/.*?-(\d+)$", response.url).groups()[0]

        properties = {
            'name': response.xpath('//span[@class="location-name-geo"]/text()').extract_first(),
            'addr_full': response.xpath('//address[@itemprop="address"]/span[@itemprop="streetAddress"]/span/text()').extract_first().strip(),
            'city': response.xpath('//span[@itemprop="addressLocality"]/text()').extract_first(),
            'state': response.xpath('//abbr[@itemprop="addressRegion"]/text()').extract_first(),
            'postcode': response.xpath('//span[@itemprop="postalCode"]/text()').extract_first().strip(),
            'ref': ref,
            'website': response.url,
            'lon': float(response.xpath('//span/meta[@itemprop="longitude"]/@content').extract_first()),
            'lat': float(response.xpath('//span/meta[@itemprop="latitude"]/@content').extract_first()),
        }

        phone = response.xpath('//a[@class="c-phone-number-link c-phone-main-number-link"]/text()').extract_first()
        if phone:
            properties['phone'] = phone

        hours = json.loads(response.xpath('//div[@class="c-location-hours-today js-location-hours"]/@data-days').extract_first())

        try:
            opening_hours = self.store_hours(hours)
        except:
            opening_hours = None
        if opening_hours:
            properties['opening_hours'] = opening_hours

        yield GeojsonPointItem(**properties)

    def parse(self, response):
        urls = response.xpath('//a[@class="c-directory-list-content-item-link"]/@href').extract()
        for path in urls:
            if path.rsplit('-', 1)[-1].isnumeric():
                # If there's only one store, the URL will have a store number at the end
                yield scrapy.Request(response.urljoin(path), callback=self.parse_store)
            else:
                yield scrapy.Request(response.urljoin(path))

        urls = response.xpath('//a[@class="c-location-grid-item-link"]/@href').extract()
        for path in urls:
            yield scrapy.Request(response.urljoin(path), callback=self.parse_store)
