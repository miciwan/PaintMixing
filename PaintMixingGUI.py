import sys
import json
import math
import os
import numpy as np
import heapq
from urllib.parse import urlparse
from itertools import combinations
import PaintMixing
import matplotlib.path
import multiprocessing 
from multiprocessing import Pool
from PyQt5.QtWidgets import (QApplication, QMainWindow, QListWidget, QPushButton, QGroupBox,QSizePolicy, QVBoxLayout, QHBoxLayout, QFrame, QWidget, QSlider, QSplitter, QColorDialog, QLabel, QListWidgetItem, QCheckBox)
from PyQt5.QtCore import Qt, QSize, QMimeData, QPoint, QObject, QThread, pyqtSignal, QVariant
from PyQt5.QtGui import QColor, QPalette, QDrag, QPainter, QPen, QImage, QPixmap

PAINT_AMOUNT_SLIDER_SCALE = 10000
MAX_NUM_PAINTS_IN_RECIPE = 4


def get_text_color( color ):
    luminance = ( (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255 ) * 2.0 - 1.0
    luminance = ( math.pow( luminance, 1/8 ) if luminance > 0 else -math.pow( -luminance, 1/8 ) ) * 0.5 + 0.5 
    return QColor.fromRgbF(1.0 - luminance, 1.0 - luminance, 1.0 - luminance)


def get_color_desc( color ):
    r_int, g_int, b_int = color.red(), color.green(), color.blue()
    r, g, b = PaintMixing.Colorimetry.rgb_int_to_float( r_int, g_int, b_int )
    x, y, z = PaintMixing.Colorimetry.rgb_to_xyz( r, g, b )
    L, a, b = PaintMixing.Colorimetry.xyz_to_Lab( x, y, z )

    return "RGB ({}, {}, {})\nXYZ ({:.3f}, {:.3f}, {:.3f})".format( r_int, g_int, b_int, x, y, z );


class ShowColorWidget(QWidget):
    def __init__( self, color, parent=None ):
        super(ShowColorWidget, self).__init__( parent )

        self.init_ui()
        self.update_color( color)

    def init_ui( self ):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(0)

        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)        
        self.layout.addWidget(self.label)

        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setMinimumHeight( 80 )
        self.setMaximumHeight( 80 )        
        
    def update_color(self, new_color):
        self.setStyleSheet("""
            QWidget {
                background-color: """ + new_color.name() + """;
                border-radius: 10px;
            }""" )

        text_color = get_text_color( new_color )

        self.color = new_color

        self.label.setText( get_color_desc( new_color ) )
        
        # Update styles
        self.label.setStyleSheet(f"color: {text_color.name()}; padding: 5px;")


class SpectraPlotWidget(QWidget):
    def __init__(self, parent=None):
        super(SpectraPlotWidget, self).__init__(parent)

        self.margins = (50, 20, 20, 80)

        self.setMinimumHeight( 400 )
        self.setMinimumWidth( 400 )
       
        self.data = {}
        self.range = ( ( 380, 730 ), ( 0, 1) )

        self.setAcceptDrops(True)  # Accept drops if specified        

        self.prep_spectral_gradient()
        
    def prep_spectral_gradient( self ):
        wavelengths = np.linspace( self.range[0][0], self.range[0][1], 32 )

        x = PaintMixing.Colorimetry.predefined_spectra["X"].sample( wavelengths )
        y = PaintMixing.Colorimetry.predefined_spectra["Y"].sample( wavelengths )
        z = PaintMixing.Colorimetry.predefined_spectra["Z"].sample( wavelengths )

        r, g, b = PaintMixing.Colorimetry.xyz_to_rgb( x, y, z )
        r, g, b = np.clip( PaintMixing.Colorimetry.gamma( r ), 0, 1 ), np.clip( PaintMixing.Colorimetry.gamma( g ), 0, 1 ), np.clip( PaintMixing.Colorimetry.gamma( b ), 0, 1 )

        gradient = ( np.stack( [ r, g, b ], -1 ) * 255 ).astype(np.uint8)

        self.spectral_gradient = QPixmap( QImage(gradient, 32, 1, 32 * 3, QImage.Format_RGB888) )

    def dragEnterEvent(self, event):
        # accept json files
        if event.mimeData().hasFormat("FileName"):
            fileUrl = event.mimeData().text()
            p = urlparse( fileUrl )
            if os.path.splitext(p.path)[1] == ".json":
                event.acceptProposedAction()

    def dropEvent(self, event):
        try:
            fileUrl = event.mimeData().text()
            p = urlparse( fileUrl )
            if os.path.splitext(p.path)[1] == ".json":
                with open(p.path[1:], 'r') as json_file:
                    data = json.load(json_file)
                    for i, spectrum in enumerate( data ):                        
                        self.add_data( spectrum["name"], PaintMixing.Spectrum( spectrum["wavelengths"], np.array(spectrum["values"]) / 100.0 ), QColor.fromRgbF(1.0, 1.0, 1.0 ) )
        except:
            pass


    def add_data( self, name, spectrum, color):
        self.data[name] = { "data" : spectrum,
                            "color" : color}

        self.update()


    def remove_data( self, name):
        if name in self.data:
            del self.data[name]
            self.update()

    def to_plot_coords( self, x, y ):
        def saturate( x ):
            return 0 if x < 0 else 1 if x > 1 else x

        plot_width = self.width() - self.margins[0] - self.margins[2]
        plot_height = self.height() - self.margins[1] - self.margins[3]

        x_local = saturate( ( x - self.range[0][0] ) / ( self.range[0][1] - self.range[0][0]) )
        y_local = saturate( ( y - self.range[1][0] ) / ( self.range[1][1] - self.range[1][0]) )

        return int( x_local * plot_width + self.margins[0] ), int( ( 1.0 - y_local ) * plot_height + self.margins[1] )


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        painter.setPen( QPen( QColor.fromRgbF(1.0, 1.0, 1.0, 0.3), 0.3, Qt.SolidLine ) )
        for wavelength in range( self.range[0][0], self.range[0][1] + 1, 50):            
            painter.drawLine( *self.to_plot_coords( wavelength, 0 ), *self.to_plot_coords( wavelength, 1 ))

            position_x, position_y = self.to_plot_coords( wavelength, 0 )            
            painter.drawText( QPoint( position_x - 10, position_y + 12 ), "{}".format( wavelength  ) )
        
        for reflectanceInt in range( 6 ):
            reflectance = reflectanceInt / 5
            painter.drawLine( *self.to_plot_coords( self.range[0][0], reflectance ), *self.to_plot_coords( self.range[0][1], reflectance ))

            position_x, position_y = self.to_plot_coords( self.range[0][0], reflectance )            
            painter.drawText( QPoint( position_x - 20, position_y + ( 0 if reflectanceInt == 0 else 10 if reflectanceInt == 5 else 5 ) ), "{:.1f}".format( reflectance ) )
        
        for name in self.data:
            spectrum = self.data[name]["data"]

            x, y = self.to_plot_coords( spectrum.wavelengths[-1], spectrum.values[-1] )
            painter.setPen( QPen( QColor.fromRgbF(1.0, 1.0, 1.0, 1.0), 0.3, Qt.SolidLine ) )            
            painter.drawText( QPoint( x - 30, y - 15 ), name )

            pen = QPen( self.data[name]["color"], 2, Qt.SolidLine )
            painter.setPen(pen)

            for i in range( 1, len( spectrum.wavelengths ) ):
                x1, y1 = self.to_plot_coords( spectrum.wavelengths[i-1], spectrum.values[i-1] )
                x2, y2 = self.to_plot_coords( spectrum.wavelengths[i], spectrum.values[i] )
                painter.drawLine(x1, y1, x2, y2)

        gradient_start_x, gradient_start_y = self.to_plot_coords( self.range[0][0], self.range[1][0] )
        gradient_end_x, gradient_end_y = self.to_plot_coords( self.range[0][1], self.range[1][0] )
        gradient_start_y = gradient_start_y + 20
        gradient_end_y = gradient_end_y + 35
        painter.drawPixmap( gradient_start_x, gradient_start_y, gradient_end_x - gradient_start_x, gradient_end_y - gradient_start_y, self.spectral_gradient )



class xyPlotWidget(QWidget):
    def __init__(self, parent=None):
        super(xyPlotWidget, self).__init__(parent)

        self.setMinimumHeight( 400 )
        self.setMinimumWidth( 400 )
        
        self.margins = (50, 20, 20, 80)
       
        self.data = {}
        self.range = ( ( 0, 0.8 ), ( 0, 0.9 ) )

        self.prep_locus()
       
    def prep_locus( self, size = 512 ):
        def to_plot( x , y ):
            return int( ( ( x - self.range[0][0] ) / ( self.range[0][1] - self.range[0][0]) ) * size  ), int( ( 1.0 - ( ( y - self.range[1][0] ) / ( self.range[1][1] - self.range[1][0]) ) ) * size  )

        self.locus_size = size

        x = np.linspace( self.range[0][0], self.range[0][1], size )
        y = np.linspace( self.range[1][1], self.range[1][0], size )
        xx, yy = np.meshgrid( x, y )
        zz = 1 - ( xx + yy )

        r, g, b = PaintMixing.Colorimetry.xyz_to_rgb( xx, yy, zz )
        r, g, b = np.clip( PaintMixing.Colorimetry.gamma( r ), 0, 1 ), np.clip( PaintMixing.Colorimetry.gamma( g ), 0, 1 ), np.clip( PaintMixing.Colorimetry.gamma( b ), 0, 1 )
        a = np.ones_like( r )

        xy_plot = ( np.stack( [ r, g, b, a ], -1 ) * 255 ).astype(np.uint8)
        
        wavelengths = np.linspace(380, 730, 128)
        locusX = PaintMixing.Colorimetry.predefined_spectra["X"].sample( wavelengths )
        locusY = PaintMixing.Colorimetry.predefined_spectra["Y"].sample( wavelengths )
        locusZ = PaintMixing.Colorimetry.predefined_spectra["Z"].sample( wavelengths )
        locus_x = locusX / ( locusX + locusY + locusZ )
        locus_y = locusY / ( locusX + locusY + locusZ )

        self.locus_points = np.stack( ( locus_x, locus_y ), -1 )

        path = matplotlib.path.Path( self.locus_points )
        xy_plot = np.where( path.contains_points(np.stack( ( xx, yy ), -1 ).reshape(-1,2)).reshape(size, size, 1), xy_plot, np.zeros_like( xy_plot ) )
          
        self.xyColorDiagram = QPixmap( QImage(xy_plot, size, size, size * 4, QImage.Format_RGBA8888) )

        self.gamuts = {}
        self.gamuts["sRGB"] = { "whitepoint" : ( 0.3127, 0.3290 ),
                                "corners" : [ ( 0.6400, 0.3300 ), ( 0.3000 , 0.6000 ), ( 0.1500, 0.0600 ) ]  }


    def add_data( self, name, spectrum, color):
        x, y, z = PaintMixing.Colorimetry.reflectance_to_xyz( spectrum )

        self.data[name] = { "data" : ( x / ( x + y + z ), y / ( x + y + z ) ),
                            "color" : color}

        self.update()

    def add_data_rgb( self, name, color ):
        x, y, z = PaintMixing.Colorimetry.rgb_to_xyz( *PaintMixing.Colorimetry.rgb_int_to_float( color.red(), color.green(), color.blue() ) )

        self.data[name] = { "data" : ( x / ( x + y + z ), y / ( x + y + z ) ),
                            "color" : color}

        self.update()

    def remove_data( self, name):
        if name in self.data:
            del self.data[name]
            self.update()

    def to_plot_coords( self, x, y ):
        def saturate( x ):
            return 0 if x < 0 else 1 if x > 1 else x

        width_no_margins = self.width() - self.margins[0] - self.margins[2]
        height_no_margins = self.height() - self.margins[1] - self.margins[3]

        min_size = width_no_margins if width_no_margins < height_no_margins else height_no_margins
        max_size = width_no_margins if width_no_margins > height_no_margins else height_no_margins
        extra_margin = ( max_size - min_size ) // 2
        extra_margin_x = extra_margin if width_no_margins > height_no_margins else 0
        extra_margin_y = extra_margin if width_no_margins < height_no_margins else 0

        plot_width = min_size
        plot_height = min_size

        x_local = saturate( ( x - self.range[0][0] ) / ( self.range[0][1] - self.range[0][0]) )
        y_local = saturate( ( y - self.range[1][0] ) / ( self.range[1][1] - self.range[1][0]) )

        return int( x_local * plot_width + self.margins[0] + extra_margin_x ), int( ( 1.0 - y_local ) * plot_height + self.margins[1] + extra_margin_y )


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        painter.setPen( QPen( QColor.fromRgbF(1.0, 1.0, 1.0, 0.3), 0.3, Qt.SolidLine ) )
        for x in np.linspace( self.range[0][0], self.range[0][1], 10):
            painter.drawLine( *self.to_plot_coords( x, 0 ), *self.to_plot_coords( x, 1 ))

            position_x, position_y = self.to_plot_coords( x, 0 )            
            painter.drawText( QPoint( position_x - 10, position_y + 12 ), "{:.2f}".format( x ) )

        for i, y in enumerate( np.linspace( self.range[1][0], self.range[1][1], 10) ):
            painter.drawLine( *self.to_plot_coords( 0, y ), *self.to_plot_coords( 1, y ))

            position_x, position_y = self.to_plot_coords( 0, y )            
            painter.drawText( QPoint( position_x - 27, position_y + ( 0  if i == 0 else 10 if i == 9 else 5 ) ), "{:.2f}".format( y ) )

        top_x, top_y = self.to_plot_coords( self.range[0][0], self.range[1][1] )
        bottom_x, bottom_y = self.to_plot_coords( self.range[0][1], self.range[0][0] )

        painter.drawPixmap( top_x, top_y, bottom_x - top_x, bottom_y - top_y, self.xyColorDiagram )

        painter.setPen( QPen( QColor.fromRgbF(0.0, 0.0, 0.0, 1.0), 1.0, Qt.SolidLine ) )
        for i in range( 0, len( self.locus_points ) ):
            x1, y1 = self.to_plot_coords( *self.locus_points[i-1] )
            x2, y2 = self.to_plot_coords( *self.locus_points[i] )
            painter.drawLine(x1, y1, x2, y2)
        
        for gamut_name in self.gamuts:
            gamut = self.gamuts[gamut_name]
            if "whitepoint" in gamut:
                painter.setPen( QPen( QColor.fromRgbF(1.0, 1.0, 1.0, 1.0), 1.0, Qt.SolidLine ) )                
                center = QPoint( *self.to_plot_coords( *gamut["whitepoint"] ) )
                painter.drawEllipse( center, 3, 3 )

            if "corners" in gamut:
                painter.setPen( QPen( QColor.fromRgbF(1.0, 1.0, 1.0, 1.0), 0.3, Qt.SolidLine ) )
                position_x, position_y = self.to_plot_coords( *gamut["corners"][0] )            
                painter.drawText( QPoint( position_x - 10, position_y + 15 ), gamut_name )

                painter.setPen( QPen( QColor.fromRgbF(0.5, 0.5, 0.5, 1.0), 1.0, Qt.SolidLine ) )
                for i in range( 0, len( gamut["corners"] ) ):                    
                    x1, y1 = self.to_plot_coords( *gamut["corners"][i-1] )
                    x2, y2 = self.to_plot_coords( *gamut["corners"][i] ) 
                    painter.drawEllipse( QPoint(x1, y1), 3, 3 )
                    painter.drawLine(x1, y1, x2, y2)

        for name in self.data:
            pen = QPen( self.data[name]["color"], 2, Qt.SolidLine )
            painter.setPen(pen)

            x,y = self.to_plot_coords( *self.data[name]["data"] )
            painter.setPen( QPen( QColor.fromRgbF(1.0, 1.0, 1.0, 1.0), 0.3, Qt.SolidLine ) )
            painter.drawEllipse( QPoint( x, y ), 3, 3 )

            painter.setPen( QPen( QColor.fromRgbF(1.0, 1.0, 1.0, 1.0), 0.3, Qt.SolidLine ) )            
            painter.drawText( QPoint( x - 10, y + 15 ), name )


class BasePaintListItem(QWidget):
    def __init__(self, text, bg_color, parent=None):
        super(BasePaintListItem, self).__init__(parent)
        self.init_ui(text)
        self.update_color(bg_color)
        self.paint_name = ""

    def set_paint_name( self, name):
        self.paint_name = name

    def get_paint_name(self):
        return self.paint_name

    def init_ui(self, text, parent=None):
        self.top_layout = QHBoxLayout(self)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(0)

        self.containter = QFrame(self)
        self.top_layout.addWidget(self.containter)
        self.layout = QHBoxLayout(self.containter)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)

        # Create the checkbox, align it to the center
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(self.checkbox.sizeHint())  # Set fixed size for checkbox
        self.checkbox.setToolTip( "If checked, paint is used when solving for recipe")
        self.layout.addWidget(self.checkbox)
        self.layout.setAlignment(self.checkbox, Qt.AlignCenter)

        # Create the label with text
        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label.setWordWrap(True)  # Ensure word wrap is enabled
        self.layout.addWidget(self.label)

        # Adjust size policy to ensure the label can expand vertically
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def update_color(self, new_color):
        self.setStyleSheet("""
            QWidget {
                background-color: """ + new_color.name() + """;
                border-radius: 10px;
            }""" )

        text_color = get_text_color( new_color )
        
        # Update styles
        self.label.setStyleSheet(f"color: {text_color.name()}; padding: 5px;")

    def sizeHint(self):            
        return QSize(100, 80)


class UsedPaintListItem(QWidget):
    def __init__(self, text, bg_color, parent=None):
        super(UsedPaintListItem, self).__init__(parent)
        self.init_ui(text)
        self.update_color(bg_color)
        self.paint_name = ""

    def set_paint_name( self, name):
        self.paint_name = name

    def get_paint_name(self):
        return self.paint_name

    def init_ui(self, text, parent=None):
        self.top_layout = QHBoxLayout(self)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(0)

        self.containter = QFrame(self)
        self.top_layout.addWidget(self.containter)
        self.layout = QVBoxLayout(self.containter)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(1)

        # Create the label with text
        self.containter = QFrame(self)
        self.containter_layout = QHBoxLayout(self.containter)
        self.containter_layout.setContentsMargins(0, 0, 10, 0)
        self.containter_layout.setSpacing(0)
        self.layout.addWidget(self.containter)

        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(self.checkbox.sizeHint())  # Set fixed size for checkbox
        self.checkbox.setToolTip( "If checked, paint reflectance is visible in the mixing plot")
        self.checkbox.setChecked( True )
        self.containter_layout.addWidget(self.checkbox)
        self.containter_layout.setAlignment(self.checkbox, Qt.AlignCenter)

        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)        
        self.containter_layout.addWidget(self.label)

        self.amount_label = QLabel("0.45")
        self.containter_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)        
        self.containter_layout.addWidget(self.amount_label)

        # Create the checkbox, align it to the center
        self.slider = QSlider( Qt.Horizontal ) 
        self.slider.setMinimum( 0 )
        self.slider.setMaximum( PAINT_AMOUNT_SLIDER_SCALE )
        self.slider.setSingleStep( 1 )
        self.layout.addWidget(self.slider)
        
        # Adjust size policy to ensure the label can expand vertically
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.slider.valueChanged.connect(self.slider_value_changed)

    def slider_value_changed( self, value ):
        self.amount_label.setText( "{:.3f}".format( value / PAINT_AMOUNT_SLIDER_SCALE ) )
    def update_color(self, new_color):
        self.setStyleSheet("""
            QWidget {
                background-color: """ + new_color.name() + """;
                border-radius: 10px;
            }""" )

        text_color = get_text_color( new_color )
        
        # Update styles
        self.label.setStyleSheet(f"color: {text_color.name()}; padding: 5px;")
        self.amount_label.setStyleSheet(f"color: {text_color.name()}; padding: 5px;")

    def sizeHint(self):            
        return QSize(100, 60)



class PaintListWidget(QListWidget):
    def __init__(self, parent=None, droppable=True):
        super(PaintListWidget, self).__init__(parent)
        self.setSpacing( 2 )
        self.setStyleSheet("""
            QListWidget {
                border: none; /* Remove border */
            }
        """)

        self.setDragEnabled(True)  # Enable dragging
        self.setAcceptDrops(True)  # Accept drops if specified
        self.setDropIndicatorShown(False)  # Show drop indicator
        self.dropCallback = None
        
    def setDropCallback( self, callback ):
        self.dropCallback = callback

    def startDrag(self, supportedActions):
        drag = QDrag(self)

        mimeData = self.mimeData(self.selectedItems()) 
        if mimeData:
            mimeData.setText( self.itemWidget(self.selectedItems()[0]).get_paint_name() )
            drag.setMimeData(mimeData)        
            drag.exec_(Qt.MoveAction)  # Use copy action for dragging

    def dropEvent(self, event):
        # Handle drop event to customize item addition
        if event.source() == self:
            event.ignore()  # Ignore if source and target are the same
        else:
            if self.dropCallback:
                self.dropCallback( event )
            else:
                event.ignore()



class PaintRecipeListItem(QWidget):
    def __init__(self, target_color, paint_database, item, parent=None):
        super(PaintRecipeListItem, self).__init__(parent)
        self.item = item
        self.paint_database = paint_database
        self.target_color = target_color
        self.recipe_picked_handler = None
        self.init_ui()
        self.update_size()        

    def init_ui(self, parent=None):
        self.top_layout = QHBoxLayout(self)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(0)

        self.containter = QFrame(self)
        self.containter.setStyleSheet("""
                QWidget {
                    background-color: """ + self.target_color.name() + """;
                    border-radius: 10px;
                }""" )
        self.top_layout.addWidget(self.containter)

        self.layout = QVBoxLayout(self.containter)        
        self.layout.setContentsMargins(70, 5, 5, 5)
        self.layout.setSpacing(5)
        
        self.recipes = {}

    def add_recipe( self, name, components ):
        mixing_components = [ ( self.paint_database.get_paint(paint_name), paint_amount ) for ( paint_name, paint_amount ) in components ]
        mixing_amount_sum = sum( paint_amount for ( paint_name, paint_amount ) in components )

        if len( mixing_components ) > 0 and mixing_amount_sum > 0:
            mixed_spectrum = self.paint_database.get_mixing_model().mix( mixing_components )

            mixed_color_rgb = PaintMixing.Colorimetry.reflectance_to_rgb( mixed_spectrum )  
            mixed_color = QColor.fromRgbF( *mixed_color_rgb )

            recipe_containter = QFrame(self)        
            recipe_containter.setStyleSheet("""
                    QWidget {
                        background-color: """ + mixed_color.name() + """;
                    }""" )
            inner_layout = QVBoxLayout( recipe_containter )        
       
            #text = "RGB ( {}, {}, {} )\n".format( mixed_color.red(), mixed_color.green(), mixed_color.blue() )
            text = get_color_desc( mixed_color ) + "\n"
            for paint_name, paint_amount in components:
                text = text + paint_name + " : " + "{:.3f}".format( paint_amount ) + "\n"
        
            text_color = get_text_color( mixed_color )

            recipe_label = QLabel( text )
            recipe_label.setStyleSheet(f"color: {text_color.name()}")
            recipe_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)          
            recipe_label.mouseDoubleClickEvent = lambda event: self.recipe_picked( name )
            inner_layout.addWidget( recipe_label )

            self.layout.addWidget( recipe_containter )

            self.recipes[name] = { "components" : components,
                                   "text" : text }

            self.update_size()
        
    def set_recipe_picked_handler( self, handler ):
        self.recipe_picked_handler = handler

    def recipe_picked( self, name ):
        if self.recipe_picked_handler:
            self.recipe_picked_handler( self.recipes[name]["components"] )

    def update_size( self ):        
        num_lines_total = 0
        for recipe in self.recipes.values():
            num_lines_total = num_lines_total + recipe["text"].count('\n') + 1

        self.item.setSizeHint( QSize( 100, 22 * num_lines_total ) )


class MainWindow(QMainWindow):
    def __init__(self, paint_database ):
        super().__init__()

        self.paint_database = paint_database
        self.used_paints = {}
        self.all_paints = {}

        self.setContentsMargins(5, 5, 5, 5)

        # Initialize the splitter layout
        self.splitter_main = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter_main)

        # All paints
        self.list_allPaints_group_box = QGroupBox(self)
        self.list_allPaints_group_box.setTitle("Base paints")
        self.splitter_main.addWidget(self.list_allPaints_group_box)

        self.list_allPaints_group_box_layout = QVBoxLayout(self.list_allPaints_group_box)

        self.list_allPaints = PaintListWidget()
        self.list_allPaints.setDropCallback( lambda event: self.dropToAllPainsList( event ) )
        self.list_allPaints_group_box_layout.addWidget(self.list_allPaints)

        # Used paints
        self.list_usedPaints_group_box = QGroupBox(self)
        self.list_usedPaints_group_box.setTitle("Used paints")
        self.splitter_main.addWidget(self.list_usedPaints_group_box)

        self.list_usedPaints_group_box_layout = QVBoxLayout(self.list_usedPaints_group_box)

        self.list_usedPaints = PaintListWidget()
        self.list_usedPaints.setDropCallback( lambda event: self.dropNewPaintToUse( event ) )
        self.list_usedPaints_group_box_layout.addWidget(self.list_usedPaints)

        # Section 'c' - mixed color, reflectance plot, Yxy space with color marked

        self.mixed_color_pane = QFrame(self)        
        self.mixed_color_layout = QVBoxLayout(self.mixed_color_pane)
        self.mixed_color_layout.setContentsMargins(0, 0, 0, 0)
        self.mixed_color_layout.setSpacing(0)

        self.mixed_color = ShowColorWidget( QColor.fromRgb( 255, 255, 255 ) )
        self.mixed_color_layout.addWidget( self.mixed_color )

        #self.figure = plt.figure()
        #self.canvas = FigureCanvas(self.figure)
        self.spectra_plot = SpectraPlotWidget()
        self.mixed_color_layout.addWidget( self.spectra_plot )

        self.locus_plot = xyPlotWidget()
        self.mixed_color_layout.addWidget( self.locus_plot )

        self.splitter_main.addWidget(self.mixed_color_pane)

        # Section 'e' - paint recipes
        self.list_recipes_group_box = QGroupBox(self)
        self.list_recipes_group_box.setTitle("Recipes")
        self.splitter_main.addWidget(self.list_recipes_group_box)
        self.list_recipes_group_box_layout = QVBoxLayout(self.list_recipes_group_box)

        #self.list_recipes_group_box_layout.setContentsMargins(0, 0, 0, 0)
        #self.list_recipes_group_box_layout.setSpacing(0)

        self.picked_color = ShowColorWidget( QColor.fromRgb( 255, 255, 255 ) )
        self.list_recipes_group_box_layout.addWidget( self.picked_color )

        self.recipe_buttons_group = QFrame(self)
        self.recipe_buttons_layout = QHBoxLayout(self.recipe_buttons_group)

        self.pick_button = QPushButton('Pick Color')
        self.pick_button.clicked.connect(self.pick_color)
        self.recipe_buttons_layout.addWidget( self.pick_button )

        self.solve_button = QPushButton('Solve')
        self.solve_button.clicked.connect(self.solve_color)
        self.recipe_buttons_layout.addWidget( self.solve_button )

        self.list_recipes_group_box_layout.addWidget( self.recipe_buttons_group )

        self.paintRecipeList = QListWidget()
        self.paintRecipeList.setSpacing( 2 )
        self.paintRecipeList.setStyleSheet("""
            QListWidget {
                border: none; /* Remove border */
            }
        """)
                
        self.list_recipes_group_box_layout.addWidget(self.paintRecipeList)

        # init paints list        
        self.populate_all_paints_list()

    def populate_all_paints_list(self):
        base_paints = self.paint_database.get_base_paints()

        for i, paint in enumerate( base_paints ):
             rgb = PaintMixing.Colorimetry.reflectance_to_rgb( self.paint_database.get_paint(paint)["reflectance"] )
             bg_color = QColor.fromRgb( int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255) )

             item = QListWidgetItem(self.list_allPaints)
             custom_widget = BasePaintListItem(f"{paint}\n" + get_color_desc( bg_color ), bg_color)
             custom_widget.set_paint_name( paint )
             custom_widget.checkbox.setChecked( True )
             item.setSizeHint(custom_widget.sizeHint())
             self.list_allPaints.addItem(item)
             self.list_allPaints.setItemWidget(item, custom_widget)

             self.all_paints[paint] = item

    
    def dropToAllPainsList( self, event ):
        if event.source() == self.list_usedPaints:
            # user dragged a paint from "used paints" onto "all paints list" - remove it from used paints
            paint_name = event.mimeData().text()
            self.remove_used_paint( paint_name )


    def dropNewPaintToUse( self, event ):        
        if event.source() == self.list_allPaints:
            # user dragged a paint from "all paints list" onto "used paints" - add it to used paints
            paint_name = event.mimeData().text()
            self.add_used_paint( paint_name, 0.5 )
        
    def add_used_paint( self, paint_name, amount ):
        if paint_name in self.used_paints.keys():
            return 

        rgb = PaintMixing.Colorimetry.reflectance_to_rgb( self.paint_database.get_paint(paint_name)["reflectance"] )
        bg_color = QColor.fromRgb( int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255) )

        item = QListWidgetItem(self.list_usedPaints)             
        custom_widget = UsedPaintListItem(paint_name, bg_color)             
        custom_widget.set_paint_name( paint_name )
        custom_widget.slider.setValue( int( amount * PAINT_AMOUNT_SLIDER_SCALE ) )
        custom_widget.slider.valueChanged.connect(self.mixing_ratios_changed)        
        custom_widget.checkbox.stateChanged.connect(lambda state: self.used_paint_flipped( paint_name, bg_color, state ) )
        item.setSizeHint(custom_widget.sizeHint())
        self.list_usedPaints.addItem(item)            
        self.list_usedPaints.setItemWidget(item, custom_widget)

        self.used_paints[paint_name] = item

        self.spectra_plot.add_data( paint_name, self.paint_database.get_paint(paint_name)["reflectance"], bg_color )
        self.locus_plot.add_data( paint_name, self.paint_database.get_paint(paint_name)["reflectance"], bg_color )
        self.mixing_ratios_changed()
    
    def remove_used_paint( self, paint_name ):
        if paint_name not in self.used_paints.keys():
            return 

        used_paint_list_item = self.used_paints[paint_name]

        if used_paint_list_item:
            self.list_usedPaints.takeItem( self.list_usedPaints.indexFromItem( used_paint_list_item ).row() )
            del self.used_paints[paint_name]

            self.spectra_plot.remove_data( paint_name )
            self.locus_plot.remove_data( paint_name )
            self.mixing_ratios_changed()

    def remove_all_used_paints( self ):
        all_used_paints = list( self.used_paints.keys() )

        for paint_name in all_used_paints:
            self.remove_used_paint( paint_name )

    def used_paint_flipped( self, paint_name, bg_color, state ):
        if state:
            self.spectra_plot.add_data( paint_name, self.paint_database.get_paint(paint_name)["reflectance"], bg_color )
            self.locus_plot.add_data( paint_name, self.paint_database.get_paint(paint_name)["reflectance"], bg_color )
        else:
            self.spectra_plot.remove_data( paint_name )
            self.locus_plot.remove_data( paint_name )                    

    def mixing_ratios_changed( self, value = None ):
        self.spectra_plot.remove_data( "mixed" );
        self.locus_plot.remove_data( "mixed" );

        all_used_paints = list( self.used_paints.keys() )

        mixing_amounts = [ ( self.list_usedPaints.itemWidget( self.used_paints[paint_name] ).slider.value() / PAINT_AMOUNT_SLIDER_SCALE ) for paint_name in all_used_paints ]
        pigments = [ self.paint_database.get_paint(paint_name) for paint_name in all_used_paints ]

        components = list( zip( pigments, mixing_amounts ) )

        if len( components ) > 0 and sum( mixing_amounts ) > 0:
            mixed_spectrum = self.paint_database.get_mixing_model().mix( components )
            mixed_color_rgb = PaintMixing.Colorimetry.reflectance_to_rgb( mixed_spectrum )  

            mixed_color = QColor.fromRgbF( *mixed_color_rgb )
            self.mixed_color.update_color( mixed_color )

            if len( components ) > 1 :
                self.spectra_plot.add_data( "mixed", mixed_spectrum, mixed_color );
                self.locus_plot.add_data( "mixed", mixed_spectrum, mixed_color );
        else:
            if len( components ) == 0:
                self.mixed_color.update_color( QColor.fromRgbF( 1, 1, 1 ) )


    def recipe_picked( self, components ):
        self.remove_all_used_paints()
        for paint, amount in components:
            self.add_used_paint( paint, amount )

    def pick_color(self):        
        color = QColorDialog.getColor()
        if color.isValid():
            self.picked_color.update_color( color )            
            self.locus_plot.add_data_rgb( "target", color )

    def solve_color(self):
        target_color = self.picked_color.color

        self.solve_button.setEnabled( False )
        self.solve_button.setText( "Solving (0/{})...".format( MAX_NUM_PAINTS_IN_RECIPE ) )

        self.paintRecipeList.clear()

        target_rgb = np.array( ( target_color.red(), target_color.green(), target_color.blue() ) ) / 255.0
        paints_to_use = [paint_name for paint_name in self.all_paints.keys() if self.list_allPaints.itemWidget( self.all_paints[paint_name] ).checkbox.isChecked()]

        self.worker = RecipeSolverWorker( target_rgb, self.paint_database, paints_to_use )
        self.thread = QThread()
        self.worker.moveToThread( self.thread )

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(lambda three_best: self.add_solved_recipe( three_best, target_color ) )

        self.thread.start()

        self.thread.finished.connect( self.solve_finished )

    def solve_finished( self ):
        self.solve_button.setEnabled( True )
        self.solve_button.setText( "Solve" )

    def add_solved_recipe( self, num_paints_three_best, target_color ):
        num_paints = num_paints_three_best[0] 
        
        self.solve_button.setText( "Solving ({}/{})...".format( num_paints, MAX_NUM_PAINTS_IN_RECIPE ) )
        
        three_best = num_paints_three_best[1:]
        item = QListWidgetItem(self.paintRecipeList)
        custom_widget = PaintRecipeListItem( target_color, self.paint_database, item )
        custom_widget.set_recipe_picked_handler( self.recipe_picked )

        for recipe_index, best_mix in enumerate( three_best ):
            num_paints = len( best_mix[2] )
            print("rgb: {}: ".format( best_mix[0] ), end = "" )

            recipe = []
            for i, paint in enumerate( best_mix[2] ):
                recipe.append( ( paint, best_mix[3][i] ) )

            custom_widget.add_recipe( "{}/{}".format( num_paints, recipe_index ), recipe )

        self.paintRecipeList.addItem(item)
        self.paintRecipeList.setItemWidget(item, custom_widget)            



class RecipeSolverWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(list)

    def __init__( self, target_rgb, paint_database, paints_to_use ):
        super().__init__()
        self.target_rgb = target_rgb
        self.paint_database = paint_database
        self.paints_to_use = paints_to_use

    def run(self):
        for num_paints in range( 1, MAX_NUM_PAINTS_IN_RECIPE + 1 ):
            paint_combinations = list( combinations( self.paints_to_use, num_paints ) )

            with Pool(min( 61, os.cpu_count() )) as p:
                results = p.map( PaintMixing.RecipeOptimizer( self.paint_database.get_all_paints(), self.target_rgb, self.paint_database.get_mixing_model() ), paint_combinations )

            three_best = heapq.nsmallest(3, results, key=lambda result: result[1])
            self.progress.emit( [ num_paints, *three_best ] )

        self.finished.emit()


class PaintMixingApp(QApplication):
    def __init__( self, argv):
        super().__init__(argv)

        self.setStyleSheet("""
                QMainWindow {
                    background-color: #323232;
                }
                QGroupBox {
                    border: 1px solid #4A4A4A;
                    padding-top: 10px;
                }
                QListWidget {
                    background-color: #424242;
                    color: #FFFFFF;
                }
                QLabel {
                    background-color: #323232;
                    color: #FFFFFF;
                }
                QSpinBox {
                    background-color: #424242;
                }
                QColorDialog {
                    background-color: #424242;
                }
                QPushButton {
                    background-color: #424242;
                    color: #FFFFFF;
                    border: 1px solid #4A4A4A;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #535353;
                }
                QPushButton:pressed {
                    background-color: #2A2A2A;
                }
                QPushButton:disabled {
                    background-color: #202020;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #999999;
                    height: 8px;
                    background: #3A3A3A;
                    margin: 2px 0;
                }
                QSlider::handle:horizontal {
                    background: #5C5C5C;
                    border: 1px solid #5C5C5C;
                    width: 18px;
                    margin: -2px 0;
                    border-radius: 3px;
                }
                QSplitter {
                    background: #424242;
                }
                QSplitter::handle {
                    background: #424242;
                }
                QSplitter::handle:hover {
                    background: #535353;
                }
                QSplitter::handle:horizontal {
                    width: 5px;
                }
                QSplitter::handle:vertical {
                    height: 5px;
                }
            """)


        #

        bundle_dir = os.path.abspath(os.path.dirname(__file__))
        paint_database = PaintMixing.PaintDatabase( [ os.path.join(bundle_dir, 'data/masstone.json'), os.path.join(bundle_dir, 'data/mix1.json') ] )

        mainWin = MainWindow( paint_database )
        mainWin.setWindowTitle("Paint Mixer")
        mainWin.show()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    app = PaintMixingApp(sys.argv)
    app.exec_()
    sys.exit(0)