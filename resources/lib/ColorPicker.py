from xml.dom.minidom import parse
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import os, math
from PIL import Image

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id').decode("utf-8")
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
COLORFILES_PATH = xbmc.translatePath("special://profile/addon_data/%s/colors/" %ADDON_ID).decode("utf-8")
SKINCOLORFILES_PATH = xbmc.translatePath("special://profile/addon_data/%s/colors/" %xbmc.getSkinDir()).decode("utf-8")
SKINCOLORFILE = xbmc.translatePath("special://skin/extras/colors/colors.xml").decode("utf-8")
WINDOW = xbmcgui.Window(10000)


def logMsg(msg, level = xbmc.LOGDEBUG):
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    xbmc.log("Skin Helper Service ColorPicker --> %s" %msg, level=level)

def try_encode(text, encoding="utf-8"):
    try:
        return text.encode(encoding,"ignore")
    except Exception:
        return text

class ColorPicker(xbmcgui.WindowXMLDialog):

    colorsList = None
    skinString = None
    winProperty = None
    shortcutProperty = None
    colorsPath = None
    savedColor = None
    currentWindow = None
    headerLabel = None
    colors_file = None
    allColors = {}
    allPalettes = []
    activePalette = None

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.buildColorsList()
        self.result = -1

        #check paths
        if xbmcvfs.exists( SKINCOLORFILE ) and not xbmcvfs.exists(SKINCOLORFILES_PATH):
            xbmcvfs.mkdirs(SKINCOLORFILES_PATH)
        if not xbmcvfs.exists(COLORFILES_PATH):
            xbmcvfs.mkdirs(COLORFILES_PATH)

    def addColorToList(self, colorname, colorstring):
        colorImageFile = self.createColorSwatchImage(colorstring)
        listitem = xbmcgui.ListItem(label=colorname, iconImage=colorImageFile)
        listitem.setProperty("colorstring",colorstring)
        self.colorsList.addItem(listitem)

    @classmethod
    def createColorSwatchImage(self, colorstring):
        colorImageFile = ""
        if colorstring:
            paths = []
            paths.append("%s%s.png"%(COLORFILES_PATH,colorstring))
            if xbmcvfs.exists( SKINCOLORFILE ):
                paths.append( "%s%s.png"%(SKINCOLORFILES_PATH,colorstring) )
            for colorImageFile in paths:
                if not xbmcvfs.exists(colorImageFile):
                    try:
                        colorstring = colorstring.strip()
                        if colorstring[0] == '#': colorstring = colorstring[1:]
                        a, r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:6], colorstring[6:]
                        a, r, g, b = [int(n, 16) for n in (a, r, g, b)]
                        color = (r, g, b, a)
                        im = Image.new("RGBA", (16, 16), color)
                        im.save(colorImageFile)
                    except:
                        logMsg("ERROR in createColorSwatchImage for colorstring: %s" %colorstring, xbmc.LOGERROR)
        return colorImageFile

    def buildColorsList(self):
        #prefer skin colors file
        if xbmcvfs.exists( SKINCOLORFILE ):
            colors_file = SKINCOLORFILE
            self.colorsPath = SKINCOLORFILES_PATH
        else:
            colors_file = os.path.join(ADDON_PATH, 'resources', 'colors','colors.xml' ).decode("utf-8")
            self.colorsPath = COLORFILES_PATH

        doc = parse( colors_file )
        paletteListing = doc.documentElement.getElementsByTagName( 'palette' )
        if paletteListing:
            #we have multiple palettes specified
            for item in paletteListing:
                paletteName = item.attributes[ 'name' ].nodeValue
                self.allColors[paletteName] = self.getColorsFromXml(item)
                self.allPalettes.append(paletteName)
        else:
            #we do not have multiple palettes
            self.allColors["all"] = self.getColorsFromXml(doc.documentElement)
            self.allPalettes.append("all")

    @classmethod
    def getColorsFromXml(self,xmlelement):
        items = []
        listing = xmlelement.getElementsByTagName( 'color' )
        for color in listing:
            name = color.attributes[ 'name' ].nodeValue.lower()
            colorstring = color.childNodes [ 0 ].nodeValue.lower()
            items.append( (name,colorstring) )
        return items

    def loadColorsForPalette(self,paletteName=""):
        self.colorsList.reset()
        if not paletteName:
            #just grab the first palette if none specified
            paletteName = self.allPalettes[0]
        # set window prop with active palette
        if paletteName != "all": self.currentWindow.setProperty("palettename",paletteName)
        if not self.allColors.get(paletteName):
            logMsg("No palette exists with name %s" %paletteName, xbmc.LOGERROR)
            return
        for item in self.allColors[paletteName]:
            self.addColorToList(item[0], item[1])

    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        self.currentWindow = xbmcgui.Window( xbmcgui.getCurrentWindowDialogId() )

        self.colorsList = self.getControl(3110)
        self.win = xbmcgui.Window( 10000 )

        #set headerLabel
        try:
            self.getControl(1).setLabel(self.headerLabel)
        except Exception:
            pass

        #get current color that is stored in the skin setting
        curvalue = ""
        curvalue_name = ""
        if self.skinString:
            curvalue = xbmc.getInfoLabel("Skin.String(%s)" %self.skinString)
            curvalue_name = xbmc.getInfoLabel("Skin.String(%s.name)" %self.skinString)
        if self.winProperty:
            curvalue = WINDOW.getProperty(self.winProperty)
            curvalue_name = xbmc.getInfoLabel('%s.name)' %self.winProperty)
        if curvalue:
            self.currentWindow.setProperty("colorstring", curvalue)
            if curvalue != curvalue_name:
                self.currentWindow.setProperty("colorname", curvalue_name)
            self.currentWindow.setProperty("current.colorstring", curvalue)
            if curvalue != curvalue_name:
                self.currentWindow.setProperty("current.colorname", curvalue_name)

        #load colors in the list
        self.loadColorsForPalette(self.activePalette)

        #focus the current color
        if self.currentWindow.getProperty("colorstring"):
            self.currentWindow.setFocusId(3010)
        else:
            #no color setup so we just focus the colorslist
            self.currentWindow.setFocusId(3110)
            self.colorsList.selectItem(0)
            self.currentWindow.setProperty("colorstring", self.colorsList.getSelectedItem().getProperty("colorstring"))
            self.currentWindow.setProperty("colorname", self.colorsList.getSelectedItem().getLabel())

        #set opacity slider
        if self.currentWindow.getProperty("colorstring"):
            self.setOpacitySlider()

        xbmc.executebuiltin( "Dialog.Close(busydialog)" )

    def onFocus(self, controlId):
        pass

    def onAction(self, action):
        ACTION_CANCEL_DIALOG = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )

        if action.getId() in ACTION_CANCEL_DIALOG:
            self.setColorSetting(restoreprevious=True)
            self.closeDialog()

    def closeDialog(self):
        self.close()

    def setOpacitySlider(self):
        colorstring = self.currentWindow.getProperty("colorstring")
        try:
            if colorstring != "" and colorstring != None and colorstring.lower() != "none":
                a, r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:6], colorstring[6:]
                a, r, g, b = [int(n, 16) for n in (a, r, g, b)]
                a = 100.0 * a / 255
                self.getControl( 3015 ).setPercent( float(a) )
        except Exception:
            pass

    def setColorSetting(self,restoreprevious=False):
        #save the selected color to the skin setting
        if restoreprevious:
            colorname = self.currentWindow.getProperty("current.colorname")
            colorstring = self.currentWindow.getProperty("current.colorstring")
        else:
            colorname = self.currentWindow.getProperty("colorname")
            colorstring = self.currentWindow.getProperty("colorstring")
        if not colorname: colorname = colorstring
        self.createColorSwatchImage(colorstring)
        if self.skinString and (not colorstring or colorstring == "None"):
            xbmc.executebuiltin("Skin.SetString(%s.name, %s)" %(try_encode(self.skinString), try_encode(ADDON.getLocalizedString(32013))))
            xbmc.executebuiltin("Skin.SetString(%s, None)" %try_encode(self.skinString))
            xbmc.executebuiltin("Skin.Reset(%s.base)" %try_encode(self.skinString))
        elif self.skinString and colorstring:
            xbmc.executebuiltin("Skin.SetString(%s.name, %s)" %(try_encode(self.skinString),try_encode(colorname)))
            colorbase = "ff" + colorstring[2:]
            xbmc.executebuiltin("Skin.SetString(%s, %s)" %(try_encode(self.skinString),try_encode(colorstring)))
            xbmc.executebuiltin("Skin.SetString(%s.base, %s)" %(try_encode(self.skinString) ,try_encode(colorbase)))
        elif self.winProperty:
            WINDOW.setProperty(self.winProperty, colorstring)
            WINDOW.setProperty(self.winProperty + ".name", colorname)

    def onClick(self, controlID):

        if controlID == 3110:
            #color clicked
            item =  self.colorsList.getSelectedItem()
            colorstring = item.getProperty("colorstring")
            self.currentWindow.setProperty("colorstring",colorstring)
            self.currentWindow.setProperty("colorname",item.getLabel())
            self.setOpacitySlider()
            self.currentWindow.setFocusId(3012)
            self.currentWindow.setProperty("color_chosen","true")
            self.setColorSetting()
        elif controlID == 3010:
            #manual input
            dialog = xbmcgui.Dialog()
            colorstring = dialog.input(ADDON.getLocalizedString(32012), self.currentWindow.getProperty("colorstring"), type=xbmcgui.INPUT_ALPHANUM)
            self.currentWindow.setProperty("colorname", ADDON.getLocalizedString(32050))
            self.currentWindow.setProperty("colorstring", colorstring)
            self.setOpacitySlider()
            self.setColorSetting()
        elif controlID == 3011:
            # none button
            self.currentWindow.setProperty("colorstring", "")
            self.setColorSetting()

        if controlID == 3012 or controlID == 3011:
            #save button clicked or none
            if self.skinString or self.winProperty:
                self.closeDialog()
            elif self.shortcutProperty:
                self.result = (self.currentWindow.getProperty("colorstring"),self.currentWindow.getProperty("colorname"))
                self.closeDialog()

        elif controlID == 3015:
            try:
                #opacity slider
                colorstring = self.currentWindow.getProperty("colorstring")
                opacity = self.getControl( 3015 ).getPercent()
                num = opacity / 100.0 * 255
                e = num - math.floor( num )
                a = e < 0.5 and int( math.floor( num ) ) or int( math.ceil( num ) )
                colorstring = colorstring.strip()
                r, g, b = colorstring[2:4], colorstring[4:6], colorstring[6:]
                r, g, b = [int(n, 16) for n in (r, g, b)]
                color = (a, r, g, b)
                colorstringvalue = '%02x%02x%02x%02x' % color
                self.currentWindow.setProperty("colorstring",colorstringvalue)
                self.setColorSetting()
            except Exception:
                pass

        elif controlID == 3030:
            #change color palette
            ret = xbmcgui.Dialog().select(ADDON.getLocalizedString(32141), self.allPalettes)
            self.loadColorsForPalette(self.allPalettes[ret])
