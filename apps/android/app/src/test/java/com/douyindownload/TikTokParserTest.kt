package com.douyindownload

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TikTokParserTest {

    @Test
    fun testExtractUrls() {
        val text = "Check this out: https://www.tiktok.com/@user/video/123456789 and this: http://v.tiktok.com/abcd/"

        val urls = TikTokParser.extractUrls(text)
        assertEquals(2, urls.size)
        assertTrue(urls.contains("https://www.tiktok.com/@user/video/123456789"))
        assertTrue(urls.contains("http://v.tiktok.com/abcd/"))
    }

    @Test
    fun testExtractMedia_Video() {
        val jsonString = """
        {
            "__DEFAULT_SCOPE__": {
                "webapp.video-detail": {
                    "itemInfo": {
                        "itemStruct": {
                            "video": {
                                "playAddr": "https://example.com/video.mp4"
                            }
                        }
                    }
                }
            }
        }
        """.trimIndent()
        val json = JSONObject(jsonString)
        
        val media = TikTokParser.extractMedia(json)
        assertEquals(1, media.size)
        assertTrue(media[0].isVideo)
        assertEquals("https://example.com/video.mp4", media[0].url)
    }

    @Test
    fun testExtractMedia_Images() {
        val jsonString = """
        {
            "__DEFAULT_SCOPE__": {
                "webapp.video-detail": {
                    "itemInfo": {
                        "itemStruct": {
                            "imagePostInfo": {
                                "images": [
                                    { "displayAddr": { "urlList": ["https://example.com/img1.jpg"] } },
                                    { "displayAddr": { "urlList": ["https://example.com/img2.jpg"] } }
                                ]
                            }
                        }
                    }
                }
            }
        }
        """.trimIndent()
        val json = JSONObject(jsonString)
        
        val media = TikTokParser.extractMedia(json)
        assertEquals(2, media.size)
        assertTrue(!media[0].isVideo)
        assertEquals("https://example.com/img1.jpg", media[0].url)
        assertTrue(!media[1].isVideo)
        assertEquals("https://example.com/img2.jpg", media[1].url)
    }
}
