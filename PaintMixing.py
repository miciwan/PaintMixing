import json
import numpy as np
import scipy
from itertools import combinations
from scipy.interpolate import interp1d


class Spectrum:
    def __init__( self, wavelengths = [], values = [ ], value_scale = 1.0 ):
        self.wavelengths = np.array( wavelengths )
        self.values = np.array( values ) * value_scale

    def __add__( self, rhs ):
        if type( rhs ) is Spectrum:
            combined_wavelengths = np.union1d(self.wavelengths, rhs.wavelengths)
    
            # Interpolate values of both spectra onto the combined wavelength array
            interp_lhs = interp1d(self.wavelengths if len( self.wavelengths ) > 0 else [ 0.0 ], self.values if len( self.wavelengths ) > 0 else [ 0.0 ], bounds_error=False, fill_value=0)
            interp_rhs = interp1d(rhs.wavelengths if len(rhs.wavelengths ) > 0 else [ 0.0 ], rhs.values if len(rhs.wavelengths ) > 0 else [ 0.0 ], bounds_error=False, fill_value=0)
    
            # Interpolated values
            lhs_interpolated_values = interp_lhs(combined_wavelengths)
            rhs_interpolated_values = interp_rhs(combined_wavelengths)
    
            # add the interpolated values
            result_values = lhs_interpolated_values + rhs_interpolated_values
    
            return Spectrum( combined_wavelengths, result_values )
        else:
            return self

    def __mul__( self, rhs ):
        if type( rhs ) is Spectrum:
            combined_wavelengths = np.union1d(self.wavelengths, rhs.wavelengths)
    
            # Interpolate values of both spectra onto the combined wavelength array
            interp_lhs = interp1d(self.wavelengths if len( self.wavelengths ) > 0 else [ 0.0 ], self.values if len( self.wavelengths ) > 0 else [ 0.0 ], bounds_error=False, fill_value=0)
            interp_rhs = interp1d(rhs.wavelengths if len(rhs.wavelengths ) > 0 else [ 0.0 ], rhs.values if len(rhs.wavelengths ) > 0 else [ 0.0 ], bounds_error=False, fill_value=0)
    
            # Interpolated values
            lhs_interpolated_values = interp_lhs(combined_wavelengths)
            rhs_interpolated_values = interp_rhs(combined_wavelengths)
    
            # Multiply the interpolated values
            result_values = lhs_interpolated_values * rhs_interpolated_values
    
            return Spectrum( combined_wavelengths, result_values )
        elif type( rhs ) is float:
            return Spectrum( self.wavelengths, self.values * rhs )
        else:
            return self

    def sample( self, wavelength ):
        return np.interp( wavelength, self.wavelengths, self.values )

    def resample( self, wavelengths ):
        interp = interp1d( self.wavelengths, self.values, bounds_error=False, fill_value=0 )
        resampled_values = interp( wavelengths )
        return Spectrum( wavelengths, resampled_values )

    def integrate( self, range_min = 380, range_max = 730 ):
        valid_indices = np.where((self.wavelengths >= range_min) & (self.wavelengths <= range_max ))
        filtered_wavelengths = self.wavelengths[valid_indices]
        filtered_values = self.values[valid_indices]

        # Use numpy's trapezoidal rule integration function
        integrated_value = np.trapz(filtered_values, filtered_wavelengths)
    
        return integrated_value


class Colorimetry:
    predefined_spectra = {
        "X" : Spectrum( [ 380.0,385.0,390.0,395.0,400.0,405.0,410.0,415.0,420.0,425.0,430.0,435.0,440.0,445.0,
                          450.0,455.0,460.0,465.0,470.0,475.0,480.0,485.0,490.0,495.0,500.0,505.0,510.0,515.0,
                          520.0,525.0,530.0,535.0,540.0,545.0,550.0,555.0,560.0,565.0,570.0,575.0,580.0,585.0,
                          590.0,595.0,600.0,605.0,610.0,615.0,620.0,625.0,630.0,635.0,640.0,645.0,650.0,655.0,
                          660.0,665.0,670.0,675.0,680.0,685.0,690.0,695.0,700.0,705.0,710.0,715.0,720.0,725.0,730.0 ],
                        [ 0.001368,0.002236,0.004243,0.007650,0.014310,0.023190,0.043510,0.077630,0.134380,0.214770,0.283900,0.328500,0.348280,0.348060,
                          0.336200,0.318700,0.290800,0.251100,0.195360,0.142100,0.095640,0.057950,0.032010,0.014700,0.004900,0.002400,0.009300,0.029100,
                          0.063270,0.109600,0.165500,0.225750,0.290400,0.359700,0.433450,0.512050,0.594500,0.678400,0.762100,0.842500,0.916300,0.978600,
                          1.026300,1.056700,1.062200,1.045600,1.002600,0.938400,0.854450,0.751400, 0.642400,0.541900,0.447900,0.360800,0.283500,0.218700,
                          0.164900,0.121200,0.087400,0.063600,0.046770,0.032900,0.022700,0.015840,0.011359,0.008111,0.005790,0.004109,0.002899,0.002049,0.001440 ] ),

        "Y" : Spectrum( [ 380.0,385.0,390.0,395.0,400.0,405.0,410.0,415.0,420.0,425.0,430.0,435.0,440.0,445.0,
                          450.0,455.0,460.0,465.0,470.0,475.0,480.0,485.0,490.0,495.0,500.0,505.0,510.0,515.0,
                          520.0,525.0,530.0,535.0,540.0,545.0,550.0,555.0,560.0,565.0,570.0,575.0,580.0,585.0,
                          590.0,595.0,600.0,605.0,610.0,615.0,620.0,625.0,630.0,635.0,640.0,645.0,650.0,655.0,
                          660.0,665.0,670.0,675.0,680.0,685.0,690.0,695.0,700.0,705.0,710.0,715.0,720.0,725.0,730.0 ],
                        [ 0.000039,0.000064,0.000120,0.000217,0.000396,0.000640,0.001210,0.002180,0.004000,0.007300,0.011600,0.016840,0.023000,0.029800,
                          0.038000,0.048000,0.060000,0.073900,0.090980,0.112600,0.139020,0.169300,0.208020,0.258600,0.323000,0.407300,0.503000,0.608200,
                          0.710000,0.793200,0.862000,0.914850,0.954000,0.980300,0.994950,1.000000,0.995000,0.978600,0.952000,0.915400,0.870000,0.816300,
                          0.757000,0.694900,0.631000,0.566800,0.503000,0.441200,0.381000,0.321000,0.265000,0.217000,0.175000,0.138200,0.107000,0.081600,
                          0.061000,0.044580,0.032000,0.023200,0.017000,0.011920,0.008210,0.005723,0.004102,0.002929,0.002091,0.001484,0.001047,0.000740,0.000520 ] ),

        "Z" : Spectrum( [ 380.0,385.0,390.0,395.0,400.0,405.0,410.0,415.0,420.0,425.0,430.0,435.0,440.0,445.0,
                          450.0,455.0,460.0,465.0,470.0,475.0,480.0,485.0,490.0,495.0,500.0,505.0,510.0,515.0,
                          520.0,525.0,530.0,535.0,540.0,545.0,550.0,555.0,560.0,565.0,570.0,575.0,580.0,585.0,
                          590.0,595.0,600.0,605.0,610.0,615.0,620.0,625.0,630.0,635.0,640.0,645.0,650.0,655.0,
                          660.0,665.0,670.0,675.0,680.0,685.0,690.0,695.0,700.0,705.0,710.0,715.0,720.0,725.0,730.0 ],
                        [ 0.006450,0.010550,0.020050,0.036210,0.067850,0.110200,0.207400,0.371300,0.645600,1.039050,1.385600,1.622960,
                          1.747060,1.782600,1.772110,1.744100,1.669200,1.528100,1.287640,1.041900,0.812950,0.616200,0.465180,0.353300,
                          0.272000,0.212300,0.158200,0.111700,0.078250,0.057250,0.042160,0.029840,0.020300,0.013400,0.008750,0.005750,
                          0.003900,0.002750,0.002100,0.001800,0.001650,0.001400,0.001100,0.001000,0.000800,0.000600,0.000340,0.000240,
                          0.000190,0.000100,0.000050,0.000030,0.000020,0.000010,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,
                          0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000 ] ),

        "D65" : Spectrum( [ 380.0,385.0,390.0,395.0,400.0,405.0,410.0,415.0,420.0,425.0,430.0,435.0,440.0,445.0,
                            450.0,455.0,460.0,465.0,470.0,475.0,480.0,485.0,490.0,495.0,500.0,505.0,510.0,515.0,
                            520.0,525.0,530.0,535.0,540.0,545.0,550.0,555.0,560.0,565.0,570.0,575.0,580.0,585.0,
                            590.0,595.0,600.0,605.0,610.0,615.0,620.0,625.0,630.0,635.0,640.0,645.0,650.0,655.0,
                            660.0,665.0,670.0,675.0,680.0,685.0,690.0,695.0,700.0,705.0,710.0,715.0,720.0,725.0,730.0 ],
                          [ 49.9755,52.3118,54.6482,68.7015,82.7549,87.1204,91.486,92.4589,93.4318,90.057,86.6823,95.7736,104.865,110.936,117.008,
                            117.41,117.812,116.336,114.861,115.392,115.923,112.367,108.811,109.082,109.354,108.578,107.802,106.296,104.79,106.239,
                            107.689,106.047,104.405,104.225,104.046,102.023,100.0,98.1671,96.3342,96.0611,95.788,92.2368,88.6856,89.3459,90.0062,
                            89.8026,89.5991,88.6489,87.6987,85.4936,83.2886,83.4939,83.6992,81.863,80.0268,80.1207,80.2146,81.2462,82.2778,80.281,
                            78.2842,74.0027,69.7213,70.6652,71.6091,72.979,74.349,67.9765,61.604,65.7448,69.8856  ] )
    }

    def gamma( x ):
        return np.where( x <= 0.0031308, 323.0 / 25.0 * x, ( 211.0 * ( x ** ( 5.0 / 12.0 ) ) - 11.0 ) / 200.0)

    def degamma( x ):
        return np.where( x <= 0.04045, 25.0 / 323.0 * x,  ( ( 200.0 * x + 11.0 ) / 211.0 ) ** ( 12.0 / 5.0 ) )

    # d65 reference by default
    def xyz_to_Lab( x, y, z, ref_x = 95.047, ref_y = 100.0, ref_z = 108.883 ):
        var_x = x / ref_x
        var_y = y / ref_y
        var_z = z / ref_z

        var_x = np.where( var_x > 0.008856, var_x ** ( 1.0 / 3.0 ), ( 7.787 * var_x ) + ( 16 / 116 ) )
        var_y = np.where( var_y > 0.008856, var_y ** ( 1.0 / 3.0 ), ( 7.787 * var_y ) + ( 16 / 116 ) )
        var_z = np.where( var_z > 0.008856, var_z ** ( 1.0 / 3.0 ), ( 7.787 * var_z ) + ( 16 / 116 ) )

        return ( 116 * var_y ) - 16, 500 * ( var_x - var_y ), 200 * ( var_y - var_z )
        
    def xyz_to_rgb( x, y, z ):
        r =  3.2406 * x + -1.5372 * y + -0.4986 * z
        g = -0.9689 * x +  1.8758 * y +  0.0415 * z
        b =  0.0557 * x + -0.2040 * y +  1.0570 * z

        return r, g, b

    def rgb_to_xyz( r, g, b ):
        x =  0.4124 * r + 0.3576 * g + 0.1805 * b
        y =  0.2126 * r + 0.7152 * g + 0.0722 * b
        z =  0.0193 * r + 0.1192 * g + 0.9505 * b

        return x, y, z

    def rgb_int_to_float( r, g, b ):
        return Colorimetry.degamma( r / 255.0 ), Colorimetry.degamma( g / 255.0 ), Colorimetry.degamma( b / 255.0 )
        
    def reflectance_to_xyz( reflectance ):
        scale = ( Colorimetry.predefined_spectra["Y"] * Colorimetry.predefined_spectra["D65"] ).integrate()

        lit = reflectance * Colorimetry.predefined_spectra["D65"]
        x = ( lit * Colorimetry.predefined_spectra["X"] ).integrate() / scale
        y = ( lit * Colorimetry.predefined_spectra["Y"] ).integrate() / scale
        z = ( lit * Colorimetry.predefined_spectra["Z"] ).integrate() / scale

        return x, y, z

    def reflectance_to_rgb( reflectance ):
        def saturate( x ):
            return 1 if x > 1 else 0 if x < 0  else x

        x, y, z = Colorimetry.reflectance_to_xyz( reflectance )
        r, g, b = Colorimetry.xyz_to_rgb( x, y, z )
        return saturate( Colorimetry.gamma(r) ), saturate( Colorimetry.gamma(g) ), saturate( Colorimetry.gamma(b) )


class TwoDiffuseFluxesModel:    
    def K_S_ratio_from_reflectance( reflectance ):
        return Spectrum( reflectance.wavelengths, ( 1 - reflectance.values ) * ( 1 - reflectance.values ) / ( 4.0 * reflectance.values ) )

    def K_from_S( reflectance, S ):
        return TwoDiffuseFluxesModel.K_S_ratio_from_reflectance( reflectance ) * S 

    def __init__( self ):
        self.paint_parameters = {}

    def init_paints( self, measurements, white_name ):
        # todo:
        # add cache instead of computing that all the time on startup
        self.compute_K_S( measurements, white_name )
    
    def compute_K_S( self, measurments, white_name ):
        self.paint_parameters = {}

        # pre-set S term for white to 1.0, derive K from that
        white_sample = measurments[white_name]
        self.paint_parameters[white_name] = {}
        self.paint_parameters[white_name]["S"] = Spectrum( white_sample["reflectance"].wavelengths, np.ones_like( white_sample["reflectance"].values ) )        
        self.paint_parameters[white_name]["K"] = TwoDiffuseFluxesModel.K_from_S( white_sample["reflectance"], self.paint_parameters[white_name]["S"] )

        # todo:
        # generate graph of dependencies, so they can be computed in proper order
        # atm, we only have mixes with white, so whatever
        masstone_mixes = {}

        for sample_name in measurments:    
            if measurments[sample_name]["type"] == "masstone":
                masstone_mixes.setdefault( sample_name, [] ).append( sample_name )
            elif measurments[sample_name]["type"] == "mix":
                for component in measurments[sample_name]["components"]:            
                    masstone_mixes.setdefault( component, [] ).append( sample_name )

        for masstone in masstone_mixes:
            sample = measurments[masstone]

            sample_name = sample["name"]

            if sample_name in self.paint_parameters.keys():
                continue

            combined_wavelengths = np.array( [] )

            mixes = masstone_mixes[masstone]
            for mix in mixes:
                if measurments[mix]["type"] == "masstone":
                    combined_wavelengths = np.union1d( combined_wavelengths, measurments[mix]["reflectance"].wavelengths )                
                elif measurments[mix]["type"] == "mix":
                    for component in measurments[mix]["components"]:
                        combined_wavelengths = np.union1d( combined_wavelengths, measurments[component]["reflectance"].wavelengths )
                else:
                    pass

            A = np.zeros( ( len( combined_wavelengths ), len( masstone_mixes[masstone] ), 2) )
            b = np.zeros( ( len( combined_wavelengths ), len( masstone_mixes[masstone] ) ) )

            mixes = masstone_mixes[masstone]
            for i, mix in enumerate( mixes ):
                if measurments[mix]["type"] == "masstone":
                    resampled_reflectance = measurments[mix]["reflectance"].resample( combined_wavelengths ).values

                    A[:,i,0] = 4.0 * resampled_reflectance
                    A[:,i,1] = - ( 1.0 - resampled_reflectance ) * ( 1.0 - resampled_reflectance )
                    b[:, i] = 0            
                elif measurments[mix]["type"] == "mix":
            
                    total_weight = 0
                    for component in measurments[mix]["components"]:
                        total_weight = total_weight + measurments[mix]["components"][component]

                    for component in measurments[mix]["components"]:
                        component_weight = measurments[mix]["components"][component]
                        component_percentage = component_weight / total_weight

                        resampled_reflectance = measurments[mix]["reflectance"].resample( combined_wavelengths ).values                    

                        if component == sample_name:
                            A[:,i,0] = 4.0 * resampled_reflectance * component_percentage
                            A[:,i,1] = - ( 1.0 - resampled_reflectance ) * ( 1.0 - resampled_reflectance ) * component_percentage
                        else:
                            resampled_K = self.paint_parameters[component]["K"].resample( combined_wavelengths ).values
                            resampled_S = self.paint_parameters[component]["S"].resample( combined_wavelengths ).values

                            b[:,i] = b[:,i] - 4.0 * resampled_reflectance * resampled_K * component_percentage
                            b[:,i] = b[:,i] + ( 1.0 - resampled_reflectance ) * ( 1.0 - resampled_reflectance ) * resampled_S * component_percentage
                else:
                    pass

            Ainv = np.linalg.pinv( A )
            x = np.einsum( "bij,bj->bi", Ainv, b )

            self.paint_parameters[sample_name] = {}
            self.paint_parameters[sample_name]["K"] = Spectrum( combined_wavelengths, x[:,0] )
            self.paint_parameters[sample_name]["S"] = Spectrum( combined_wavelengths, x[:,1] )

        for masstone in masstone_mixes:
            mixes = masstone_mixes[masstone]

            for i, mix in enumerate( mixes ):
                if measurments[mix]["type"] == "masstone":
                    mixed_R = self.mix( [ ( measurments[mix], 1.0 ) ] )

                elif measurments[mix]["type"] == "mix":
            
                    mix_elements = []
                
                    for component in measurments[mix]["components"]:
                        mix_elements.append( ( measurments[component], measurments[mix]["components"][component] ) )

                    mixed_R = self.mix( mix_elements )

                combined_wavelengths = np.union1d( mixed_R.wavelengths, measurments[mix]["reflectance"].wavelengths ) 

                mixed_R_resampled = mixed_R.resample( combined_wavelengths ).values
                reflectance_resampled = measurments[mix]["reflectance"].resample( combined_wavelengths ).values

                diff = mixed_R_resampled - reflectance_resampled

                assert diff.sum() < 0.001   # there should only be some numerical differences, given we only have a masstone and a single mix

    def mix( self, components ):
        combined_wavelengths = np.array( [] )

        total_weight = 0
        for component, weight in components:
            total_weight = total_weight + weight
            combined_wavelengths = np.union1d( combined_wavelengths, self.paint_parameters[component["name"]]["K"].wavelengths ) 
            combined_wavelengths = np.union1d( combined_wavelengths, self.paint_parameters[component["name"]]["S"].wavelengths ) 

        mixed_K = np.zeros_like( combined_wavelengths )
        mixed_S = np.zeros_like( combined_wavelengths )

        if total_weight == 0:
            total_weight = 1.0

        for component, weight in components:
            component_weight = weight / total_weight
            resampled_K = self.paint_parameters[component["name"]]["K"].resample( combined_wavelengths ).values
            resampled_S = self.paint_parameters[component["name"]]["S"].resample( combined_wavelengths ).values

            mixed_K = mixed_K + resampled_K * component_weight 
            mixed_S = mixed_S + resampled_S * component_weight 

        omega = mixed_S / ( mixed_K + mixed_S )
        mixed_R = omega / ( 2.0 - omega + 2.0 * np.sqrt( 1.0 - omega ) )

        return Spectrum( combined_wavelengths, mixed_R )

class RecipeOptimizer:
    def __init__( self, base_paints, target_rgb, pigment_model ):
        self.base_paints = base_paints
        self.target_rgb = target_rgb
        self.target_lab = np.array( Colorimetry.xyz_to_Lab( *Colorimetry.rgb_to_xyz( *Colorimetry.rgb_int_to_float( *( target_rgb * 255 ) ) ) ) )
        self.pigment_model = pigment_model
        
    def mix_current_set( self, paint_set, weights ):
        components = [ ( pigment, amount ) for pigment, amount in zip( [self.base_paints[paint] for paint in paint_set], weights ) ]
        mixed_paint = self.pigment_model.mix( components )
        return mixed_paint

    def __call__( self, paint_set ):
        def func( weights ):
            mixed_paint = self.mix_current_set( paint_set, weights )

            # in sRGB
            mixed_rgb = np.array( Colorimetry.reflectance_to_rgb( mixed_paint ) )
            diff = mixed_rgb - self.target_rgb

            # in Lab
            #mixed_lab = np.array( Colorimetry.xyz_to_Lab( *Colorimetry.reflectance_to_xyz( mixed_paint ) ) ) 
            #diff = mixed_lab - self.target_lab
            
            return np.dot( diff, diff )

        #optimized_weights = scipy.optimize.minimize( func, np.array( [ 0.5 ] * len( paint_set ) ), method = "Nelder-Mead",  bounds = [(0.001, 1)] )        
        optimized_weights = scipy.optimize.minimize( func, np.array( [ 0.5 ] * len( paint_set ) ), bounds = [(0.001, 1)] )        
        mixed_rgb = np.array( Colorimetry.reflectance_to_rgb( self.mix_current_set( paint_set, optimized_weights["x"] ) ) )
        diff = np.dot( mixed_rgb - self.target_rgb, mixed_rgb - self.target_rgb )

        return mixed_rgb, diff, paint_set, optimized_weights["x"]



def load_measurments( file_path ):
    data = {}
    
    with open(file_path, 'r') as json_file:
        datasets = json.load(json_file)

        wavelengths = []

        for dataset in datasets:
            if dataset["type"] == "wavelengths":
                wavelengths = np.array( dataset["values"] )
                break

        if len( wavelengths ) == 0:
            return {}        

        for dataset in datasets:
            if dataset["type"] != "wavelengths":            
                dataset["reflectance"] = Spectrum( wavelengths, dataset["reflectance"], 1.0 / 100.0 )
                data.setdefault( dataset["name"], [] ).append( dataset )

    data = average_measurements( data )

    return data


def average_measurements( samples ):
    averaged_samples = {}

    for sample in samples:
        averaged_spectrum = Spectrum()

        if type( samples[sample] ) is list:
            for measurement in samples[sample]:
                averaged_spectrum = averaged_spectrum + measurement["reflectance"]

            averaged_spectrum = averaged_spectrum * ( 1.0 / len( samples[sample] ) )

            new_sample = dict( samples[sample][0] )
            new_sample["reflectance"] = averaged_spectrum
        else:
            new_sample = dict( samples[sample] )
            
        averaged_samples[new_sample["name"]] = new_sample

    return averaged_samples



class PaintDatabase:
    def __init__( self, measurement_files ):
        self.colorimetry = Colorimetry()
        
        self.measurments = {}
        for file_path in measurement_files:
            self.measurments = { **self.measurments, **load_measurments( file_path ) }
    
        self.mixing_model = TwoDiffuseFluxesModel()
        self.mixing_model.init_paints( self.measurments, "white" )

        self.masstones = [ k for k in self.measurments.keys() if self.measurments[k]["type"] == "masstone" ]


    def get_base_paints( self ):
        return self.masstones

    def get_paint( self, name  ):
        return self.measurments[name]

    def get_all_paints( self ):
        return self.measurments

    def get_mixing_model( self ):
        return self.mixing_model
        
