# Python task script example. It must be installed in TaskInstaller.xml to be executed.
# On Linux, you need to install jep (pip install jep) and include jep.so in LD_LIBRARY_PATH.
# see https://github.com/sepinf-inc/IPED/wiki/User-Manual#python-modules

import requests
import logging
import os
import json

'''
Description
- Translate text from items in defined categories via LibreTranslate
- Translation is attached as a SubItem
- a LibreTranslate server must be running. Installation and configuration: https://github.com/LibreTranslate/LibreTranslate
 - to create the API key DB, first run libretranslate --api-key
- translated items can be filtered with translated:true
Changelog
2024-04-21
    - first Release
'''

configFile = 'translatetext.json'

logging.basicConfig(format='%(asctime)s [%(levelname)s] [TranslateTextTask.py] %(message)s', level=logging.DEBUG)
# The main class name must be equal to the script file name without .py extension
# One instance of this class is created by each processing thread and each thread calls the implemented methods of its own object.
class TranslateTextTask:

    config = None
    # Returns if this task is enabled or not. This could access options read by init() method.
    def isEnabled(self):
        return True

    # Returns an optional list of configurable objects that can load/save parameters from/to config files. 
    def getConfigurables(self):
        return []

    # Do some task initialization, like reading options, custom config files or model.
    # It is executed when application starts by each processing thread on its class instance.
    # @Params
    # configuration:    configuration manager by which configurables can be retrieved after populated.
    def init(self, configuration):
        if TranslateTextTask.config is not None:
            return
        from java.lang import System
        ipedRoot = System.getProperty('iped.root')
        with open(os.path.join(ipedRoot, 'conf', configFile)) as f:
            TranslateTextTask.config = json.load(f)
        return
    
    
    # Finish method run after processing all items in case, e.g. to clean resources.
    # It is executed by each processing thread on its class instance.
    # Objects "ipedCase" and "searcher" are provided, so case can be queried for items and bookmarks can be created, for example.
    # TODO: document methods of those objects.
    def finish(self):
        return

    
    # Process an Item object.

    def process(self, item):
        subItemID = 0
        item_name = item.getName()
        hash = item.getHash()
        if (hash is None) or (len(hash) < 1):
            return
        media_type = item.getMediaType().toString()

        host = TranslateTextTask.config.get('host')
        port = TranslateTextTask.config.get('port')
        api_key = TranslateTextTask.config.get('api_key')
        target_language = TranslateTextTask.config.get('target_language')
        maxChars = TranslateTextTask.config.get('maxChars')
        categories = TranslateTextTask.config.get('categories')

        url = '%s:%s/translate' % ( host, port)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        meta_data = item.getMetadata()
        HashDB_Status = item.getExtraAttribute('hashDb:status')
        # set HashDB_Status as list with empty element
        # to prevent error in if statement
        if HashDB_Status is None:
            HashDB_Status = ['']

        if not item.getExtraAttribute("language:detected_1") is None:
            src_lang = item.getExtraAttribute("language:detected_1")
        else:
            src_lang= "??"
        # Only processing, if item in allowed categories, source lang not target lang and not already translated and not known by hash
        if item.getCategories() in categories and src_lang != target_language and 'known' not in HashDB_Status:
            if item.getParsedTextCache() is not None:
                if maxChars > 0:
                    Text2Translate = item.getParsedTextCache()[0:maxChars]
                else:
                    Text2Translate = item.getParsedTextCache()
                data = {
                    'q' : Text2Translate,
                    'source': 'auto',
                    'target': target_language,
                    'format' : 'text',
                    'api_key': api_key
                    }
                response = requests.post(url=url, headers=headers, data=data)
                if response.status_code == 200:
                    US_TMP = eval(response.text)
                    UEBERSETZUNG = US_TMP.get('translatedText')
                    #meta_data.set("text\:translated", "1")
                    item.setExtraAttribute("translated", True)
                    logging.info("Text translated from item %s of media type %s with hash %s", item_name, media_type, hash)
                    logging.info("set new SubItem for item %s" , item_name)
                    newSubItem(self, item, UEBERSETZUNG, subItemID)
                    subItemID += 1
                else:
                    logging.info("Error: Text not translated from item %s of media type %s with hash %s", item_name, media_type, hash)
                    item.setExtraAttribute("translation_error", response.text)


def newSubItem(self, item, text, subItemID):
    from iped.engine.data import Item

    newItem = Item()
    newItem.setParent(item)
    newItem.setName('TranslatetedText_' + str(subItemID))
    newItem.setPath(item.getPath() + ">>" + newItem.getName())
    newItem.setSubItem(True)
    newItem.setSubitemId(subItemID)
    newItem.setSumVolume(False);

    # export item content to case storage
    from iped.engine.task import ExportFileTask
    from org.apache.commons.lang3 import StringUtils
    from java.io import ByteArrayInputStream
    exporter = ExportFileTask();
    exporter.setWorker(worker);
    bytes = StringUtils.getBytes(text, 'UTF-8')
    dataStream = ByteArrayInputStream(bytes);
    exporter.extractFile(dataStream, newItem, item.getLength());

    from iped.engine.core import Statistics
    Statistics.get().incSubitemsDiscovered();

    worker.processNewItem(newItem);
