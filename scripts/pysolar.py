#!/usr/bin/python

#    Copyright 2007-2010 Brandon Stafford
#
#    This file is part of Pysolar.
#
#    Pysolar is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    Pysolar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with Pysolar. If not, see <http://www.gnu.org/licenses/>.

"""Solar geometry functions

This module contains the most important functions for calculation of the position of the sun.

"""
import math
import datetime

"""This file is consists of numerical constants for calculating corrections,
such as the wiggling ("nutation") of the axis of the earth. It also includes
functions for building dictionaries of polynomial functions for rapid
calculation of corrections.

Most of the constants come from a 2005 paper by Reda and Andreas:

I. Reda and A. Andreas, "Solar Position Algorithm for Solar Radiation
Applications," National Renewable Energy Laboratory, NREL/TP-560-34302,
revised November 2005.

http://www.osti.gov/bridge/servlets/purl/15003974-iP3z6k/native/15003974.PDF

However, it seems that Reda and Andreas took the bulk of the constants
(L0, etc.) from Pierre Bretagnon and Gerard Francou's Variations Seculaires
des Orbites Planetaires, or VSOP87:

http://en.wikipedia.org/wiki/Secular_variations_of_the_planetary_orbits#VSOP87

See also ftp://ftp.imcce.fr/pub/ephem/planets/vsop87/VSOP87D.ear

"""

def buildPolyFit((a, b, c, d)): 
    return (lambda x: a + b * x + c * x ** 2 + (x ** 3) / d)

def buildPolyDict():
    """This function builds a dictionary of polynomial functions from a list of
    coefficients, so that the functions can be called by name. This is used in
    calculating nutation.

    """
    return dict([(name, buildPolyFit(coeffs)) for (name, coeffs) in coeff_list])


coeff_list = [
    ('ArgumentOfLatitudeOfMoon', (93.27191, 483202.017538, -0.0036825, 327270.0)),
    ('LongitudeOfAscendingNode', (125.04452, -1934.136261, 0.0020708, 450000.0)),
    ('MeanElongationOfMoon', (297.85036, 445267.111480, -0.0019142, 189474.0)),
    ('MeanAnomalyOfMoon', (134.96298, 477198.867398, 0.0086972, 56250.0)),
    ('MeanAnomalyOfSun', (357.52772, 35999.050340, -0.0001603, -300000.0))
]

earth_radius = 6378140.0 # meters

aberration_sin_terms = [[0,0,0,0,1],
                        [-2,0,0,2,2],
                        [0,0,0,2,2],
                        [0,0,0,0,2],
                        [0,1,0,0,0],
                        [0,0,1,0,0],
                        [-2,1,0,2,2],
                        [0,0,0,2,1],
                        [0,0,1,2,2],
                        [-2,-1,0,2,2],
                        [-2,0,1,0,0],
                        [-2,0,0,2,1],
                        [0,0,-1,2,2],
                        [2,0,0,0,0],
                        [0,0,1,0,1],
                        [2,0,-1,2,2],
                        [0,0,-1,0,1],
                        [0,0,1,2,1],
                        [-2,0,2,0,0],
                        [0,0,-2,2,1],
                        [2,0,0,2,2],
                        [0,0,2,2,2],
                        [0,0,2,0,0],
                        [-2,0,1,2,2],
                        [0,0,0,2,0],
                        [-2,0,0,2,0],
                        [0,0,-1,2,1],
                        [0,2,0,0,0],
                        [2,0,-1,0,1],
                        [-2,2,0,2,2],
                        [0,1,0,0,1],
                        [-2,0,1,0,1],
                        [0,-1,0,0,1],
                        [0,0,2,-2,0],
                        [2,0,-1,2,1],
                        [2,0,1,2,2],
                        [0,1,0,2,2],
                        [-2,1,1,0,0],
                        [0,-1,0,2,2],
                        [2,0,0,2,1],
                        [2,0,1,0,0],
                        [-2,0,2,2,2],
                        [-2,0,1,2,1],
                        [2,0,-2,0,1],
                        [2,0,0,0,1],
                        [0,-1,1,0,0],
                        [-2,-1,0,2,1],
                        [-2,0,0,0,1],
                        [0,0,2,2,1],
                        [-2,0,2,0,1],
                        [-2,1,0,2,1],
                        [0,0,1,-2,0],
                        [-1,0,1,0,0],
                        [-2,1,0,0,0],
                        [1,0,0,0,0],
                        [0,0,1,2,0],
                        [0,0,-2,2,2],
                        [-1,-1,1,0,0],
                        [0,1,1,0,0],
                        [0,-1,1,2,2],
                        [2,-1,-1,2,2],
                        [0,0,3,2,2],
                        [2,-1,0,2,2]]

nutation_coefficients = [[-171996,-174.2,92025,8.9],
                         [-13187,-1.6,5736,-3.1],
                         [-2274,-0.2,977,-0.5],
                         [2062,0.2,-895,0.5],
                         [1426,-3.4,54,-0.1],
                         [712,0.1,-7,0],
                         [-517,1.2,224,-0.6],
                         [-386,-0.4,200,0],
                         [-301,0,129,-0.1],
                         [217,-0.5,-95,0.3],
                         [-158,0,0,0],
                         [129,0.1,-70,0],
                         [123,0,-53,0],
                         [63,0,0,0],
                         [63,0.1,-33,0],
                         [-59,0,26,0],
                         [-58,-0.1,32,0],
                         [-51,0,27,0],
                         [48,0,0,0],
                         [46,0,-24,0],
                         [-38,0,16,0],
                         [-31,0,13,0],
                         [29,0,0,0],
                         [29,0,-12,0],
                         [26,0,0,0],
                         [-22,0,0,0],
                         [21,0,-10,0],
                         [17,-0.1,0,0],
                         [16,0,-8,0],
                         [-16,0.1,7,0],
                         [-15,0,9,0],
                         [-13,0,7,0],
                         [-12,0,6,0],
                         [11,0,0,0],
                         [-10,0,5,0],
                         [-8,0,3,0],
                         [7,0,-3,0],
                         [-7,0,0,0],
                         [-7,0,3,0],
                         [-7,0,3,0],
                         [6,0,0,0],
                         [6,0,-3,0],
                         [6,0,-3,0],
                         [-6,0,3,0],
                         [-6,0,3,0],
                         [5,0,0,0],
                         [-5,0,3,0],
                         [-5,0,3,0],
                         [-5,0,3,0],
                         [4,0,0,0],
                         [4,0,0,0],
                         [4,0,0,0],
                         [-4,0,0,0],
                         [-4,0,0,0],
                         [-4,0,0,0],
                         [3,0,0,0],
                         [-3,0,0,0],
                         [-3,0,0,0],
                         [-3,0,0,0],
                         [-3,0,0,0],
                         [-3,0,0,0],
                         [-3,0,0,0],
                         [-3,0,0,0]]

L0 = [[175347046.0,0,0],
[3341656.0,4.6692568,6283.07585],
[34894.0,4.6261,12566.1517],
[3497.0,2.7441,5753.3849],
[3418.0,2.8289,3.5231],
[3136.0,3.6277,77713.7715],
[2676.0,4.4181,7860.4194],
[2343.0,6.1352,3930.2097],
[1324.0,0.7425,11506.7698],
[1273.0,2.0371,529.691],
[1199.0,1.1096,1577.3435],
[990,5.233,5884.927],
[902,2.045,26.298],
[857,3.508,398.149],
[780,1.179,5223.694],
[753,2.533,5507.553],
[505,4.583,18849.228],
[492,4.205,775.523],
[357,2.92,0.067],
[317,5.849,11790.629],
[284,1.899,796.298],
[271,0.315,10977.079],
[243,0.345,5486.778],
[206,4.806,2544.314],
[205,1.869,5573.143],
[202,2.4458,6069.777],
[156,0.833,213.299],
[132,3.411,2942.463],
[126,1.083,20.775],
[115,0.645,0.98],
[103,0.636,4694.003],
[102,0.976,15720.839],
[102,4.267,7.114],
[99,6.21,2146.17],
[98,0.68,155.42],
[86,5.98,161000.69],
[85,1.3,6275.96],
[85,3.67,71430.7],
[80,1.81,17260.15],
[79,3.04,12036.46],
[71,1.76,5088.63],
[74,3.5,3154.69],
[74,4.68,801.82],
[70,0.83,9437.76],
[62,3.98,8827.39],
[61,1.82,7084.9],
[57,2.78,6286.6],
[56,4.39,14143.5],
[56,3.47,6279.55],
[52,0.19,12139.55],
[52,1.33,1748.02],
[51,0.28,5856.48],
[49,0.49,1194.45],
[41,5.37,8429.24],
[41,2.4,19651.05],
[39,6.17,10447.39],
[37,6.04,10213.29],
[37,2.57,1059.38],
[36,1.71,2352.87],
[36,1.78,6812.77],
[33,0.59,17789.85],
[30,0.44,83996.85],
[30,2.74,1349.87],
[25,3.16,4690.48]]

L1 = [[628331966747.0,0,0],
[206059.0,2.678235,6283.07585],
[4303.0,2.6351,12566.1517],
[425.0,1.59,3.523],
[119.0,5.796,26.298],
[109.0,2.966,1577.344],
[93,2.59,18849.23],
[72,1.14,529.69],
[68,1.87,398.15],
[67,4.41,5507.55],
[59,2.89,5223.69],
[56,2.17,155.42],
[45,0.4,796.3],
[36,0.47,775.52],
[29,2.65,7.11],
[21,5.34,0.98],
[19,1.85,5486.78],
[19,4.97,213.3],
[17,2.99,6275.96],
[16,0.03,2544.31],
[16,1.43,2146.17],
[15,1.21,10977.08],
[12,2.83,1748.02],
[12,3.26,5088.63],
[12,5.27,1194.45],
[12,2.08,4694],
[11,0.77,553.57],
[10,1.3,3286.6],
[10,4.24,1349.87],
[9,2.7,242.73],
[9,5.64,951.72],
[8,5.3,2352.87],
[6,2.65,9437.76],
[6,4.67,4690.48]]

L2 = [[52919.0,0,0],
[8720.0,1.0721,6283.0758],
[309.0,0.867,12566.152],
[27,0.05,3.52],
[16,5.19,26.3],
[16,3.68,155.42],
[10,0.76,18849.23],
[9,2.06,77713.77],
[7,0.83,775.52],
[5,4.66,1577.34],
[4,1.03,7.11],
[4,3.44,5573.14],
[3,5.14,796.3],
[3,6.05,5507.55],
[3,1.19,242.73],
[3,6.12,529.69],
[3,0.31,398.15],
[3,2.28,553.57],
[2,4.38,5223.69],
[2,3.75,0.98]]

L3 = [[289.0,5.844,6283.076],
[35,0,0],
[17,5.49,12566.15],
[3,5.2,155.42],
[1,4.72,3.52],
[1,5.3,18849.23],
[1,5.97,242.73]]

L4 = [[114.0,3.142,0],
[8,4.13,6283.08],
[1,3.84,12566.15]]

L5 = [[1,3.14,0]]

B0 = [[280.0,3.199,84334.662],
[102.0,5.422,5507.553],
[80,3.88,5223.69],
[44,3.7,2352.87],
[32,4,1577.34]]

B1 = [[9,3.9,5507.55],
[6,1.73,5223.69]]


R0 = [[100013989.0,0,0],
[1670700.0,3.0984635,6283.07585],
[13956.0,3.05525,12566.1517],
[3084.0,5.1985,77713.7715],
[1628.0,1.1739,5753.3849],
[1576.0,2.8469,7860.4194],
[925.0,5.453,11506.77],
[542.0,4.564,3930.21],
[472.0,3.661,5884.927],
[346.0,0.964,5507.553],
[329.0,5.9,5223.694],
[307.0,0.299,5573.143],
[243.0,4.273,11790.629],
[212.0,5.847,1577.344],
[186.0,5.022,10977.079],
[175.0,3.012,18849.228],
[110.0,5.055,5486.778],
[98,0.89,6069.78],
[86,5.69,15720.84],
[86,1.27,161000.69],
[85,0.27,17260.15],
[63,0.92,529.69],
[57,2.01,83996.85],
[56,5.24,71430.7],
[49,3.25,2544.31],
[47,2.58,775.52],
[45,5.54,9437.76],
[43,6.01,6275.96],     
[39,5.36,4694],
[38,2.39,8827.39],
[37,0.83,19651.05],
[37,4.9,12139.55],
[36,1.67,12036.46],
[35,1.84,2942.46],
[33,0.24,7084.9],
[32,0.18,5088.63], 
[32,1.78,398.15],
[28,1.21,6286.6],
[28,1.9,6279.55],
[26,4.59,10447.39]]

R1 = [[103019.0,1.10749,6283.07585],
[1721.0,1.0644,12566.1517],
[702.0,3.142,0],
[32,1.02,18849.23],
[31,2.84,5507.55],
[25,1.32,5223.69],
[18,1.42,1577.34],
[10,5.91,10977.08],
[9,1.42,6275.96],
[9,0.27,5486.78]]

R2 = [[4359.0,5.7846,6283.0758],
[124.0,5.579,12566.152],
[12,3.14,0],
[9,3.63,77713.77],
[6,1.87,5573.14],
[3,5.47,18849]]

R3 = [[145.0,4.273,6283.076],
[7,3.92,12566.15]]

R4 = [[4,2.56,6283.08]]

def SolarTest():
        latitude_deg = 42.364908
        longitude_deg = -71.112828
        d = datetime.datetime.utcnow()
        thirty_minutes = datetime.timedelta(hours = 0.5)
        for i in range(48):
                timestamp = d.ctime()
                altitude_deg = GetAltitude(latitude_deg, longitude_deg, d)
                azimuth_deg = GetAzimuth(latitude_deg, longitude_deg, d)
                power = GetRadiationDirect(d, altitude_deg)
                if (altitude_deg > 0):
                        print timestamp, "UTC", altitude_deg, azimuth_deg, power
                d = d + thirty_minutes

def EquationOfTime(day):
        b = (2 * math.pi / 364.0) * (day - 81)
        return (9.87 * math.sin(2 *b)) - (7.53 * math.cos(b)) - (1.5 * math.sin(b))

def GetAberrationCorrection(radius_vector): 	# r is earth radius vector [astronomical units]
        return -20.4898/(3600.0 * radius_vector)

def GetAltitude(latitude_deg, longitude_deg, utc_datetime, elevation = 0, temperature_celsius = 25, pressure_millibars = 1013.25):
        '''See also the faster, but less accurate, GetAltitudeFast()'''
        # location-dependent calculations	
        projected_radial_distance = GetProjectedRadialDistance(elevation, latitude_deg)
        projected_axial_distance = GetProjectedAxialDistance(elevation, latitude_deg)

        # time-dependent calculations	
        jd = GetJulianDay(utc_datetime)
        jde = GetJulianEphemerisDay(jd, 65)
        jce = GetJulianEphemerisCentury(jde)
        jme = GetJulianEphemerisMillenium(jce)
        geocentric_latitude = GetGeocentricLatitude(jme)
        geocentric_longitude = GetGeocentricLongitude(jme)
        radius_vector = GetRadiusVector(jme)
        aberration_correction = GetAberrationCorrection(radius_vector)
        equatorial_horizontal_parallax = GetEquatorialHorizontalParallax(radius_vector)
        nutation = GetNutation(jde)
        apparent_sidereal_time = GetApparentSiderealTime(jd, jme, nutation)
        true_ecliptic_obliquity = GetTrueEclipticObliquity(jme, nutation)

        # calculations dependent on location and time
        apparent_sun_longitude = GetApparentSunLongitude(geocentric_longitude, nutation, aberration_correction)
        geocentric_sun_right_ascension = GetGeocentricSunRightAscension(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
        geocentric_sun_declination = GetGeocentricSunDeclination(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
        local_hour_angle = GetLocalHourAngle(apparent_sidereal_time, longitude_deg, geocentric_sun_right_ascension)
        parallax_sun_right_ascension = GetParallaxSunRightAscension(projected_radial_distance, equatorial_horizontal_parallax, local_hour_angle, geocentric_sun_declination)
        topocentric_local_hour_angle = GetTopocentricLocalHourAngle(local_hour_angle, parallax_sun_right_ascension)
        topocentric_sun_declination = GetTopocentricSunDeclination(geocentric_sun_declination, projected_axial_distance, equatorial_horizontal_parallax, parallax_sun_right_ascension, local_hour_angle)
        topocentric_elevation_angle = GetTopocentricElevationAngle(latitude_deg, topocentric_sun_declination, topocentric_local_hour_angle)
        refraction_correction = GetRefractionCorrection(pressure_millibars, temperature_celsius, topocentric_elevation_angle)
        return topocentric_elevation_angle + refraction_correction

def GetAltitudeFast(latitude_deg, longitude_deg, utc_datetime):

# expect 19 degrees for solar.GetAltitude(42.364908,-71.112828,datetime.datetime(2007, 2, 18, 20, 13, 1, 130320))

        day = GetDayOfYear(utc_datetime)
        declination_rad = math.radians(GetDeclination(day))
        latitude_rad = math.radians(latitude_deg)
        hour_angle = GetHourAngle(utc_datetime, longitude_deg)

        first_term = math.cos(latitude_rad) * math.cos(declination_rad) * math.cos(math.radians(hour_angle))
        second_term = math.sin(latitude_rad) * math.sin(declination_rad)
        return math.degrees(math.asin(first_term + second_term))

def GetApparentSiderealTime(julian_day, jme, nutation):
        return GetMeanSiderealTime(julian_day) + nutation['longitude'] * math.cos(GetTrueEclipticObliquity(jme, nutation))

def GetApparentSunLongitude(geocentric_longitude, nutation, ab_correction):
        return geocentric_longitude + nutation['longitude'] + ab_correction

def GetAzimuth(latitude_deg, longitude_deg, utc_datetime, elevation = 0):

        # location-dependent calculations	
        projected_radial_distance = GetProjectedRadialDistance(elevation, latitude_deg)
        projected_axial_distance = GetProjectedAxialDistance(elevation, latitude_deg)

        # time-dependent calculations	
        jd = GetJulianDay(utc_datetime)
        jde = GetJulianEphemerisDay(jd, 65)
        jce = GetJulianEphemerisCentury(jde)
        jme = GetJulianEphemerisMillenium(jce)
        geocentric_latitude = GetGeocentricLatitude(jme)
        geocentric_longitude = GetGeocentricLongitude(jme)
        radius_vector = GetRadiusVector(jme)
        aberration_correction = GetAberrationCorrection(radius_vector)
        equatorial_horizontal_parallax = GetEquatorialHorizontalParallax(radius_vector)
        nutation = GetNutation(jde)
        apparent_sidereal_time = GetApparentSiderealTime(jd, jme, nutation)
        true_ecliptic_obliquity = GetTrueEclipticObliquity(jme, nutation)

        # calculations dependent on location and time
        apparent_sun_longitude = GetApparentSunLongitude(geocentric_longitude, nutation, aberration_correction)
        geocentric_sun_right_ascension = GetGeocentricSunRightAscension(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
        geocentric_sun_declination = GetGeocentricSunDeclination(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
        local_hour_angle = GetLocalHourAngle(apparent_sidereal_time, longitude_deg, geocentric_sun_right_ascension)
        parallax_sun_right_ascension = GetParallaxSunRightAscension(projected_radial_distance, equatorial_horizontal_parallax, local_hour_angle, geocentric_sun_declination)
        topocentric_local_hour_angle = GetTopocentricLocalHourAngle(local_hour_angle, parallax_sun_right_ascension)
        topocentric_sun_declination = GetTopocentricSunDeclination(geocentric_sun_declination, projected_axial_distance, equatorial_horizontal_parallax, parallax_sun_right_ascension, local_hour_angle)
        return 180 - GetTopocentricAzimuthAngle(topocentric_local_hour_angle, latitude_deg, topocentric_sun_declination)

def GetAzimuthFast(latitude_deg, longitude_deg, utc_datetime):
# expect -50 degrees for solar.GetAzimuth(42.364908,-71.112828,datetime.datetime(2007, 2, 18, 20, 18, 0, 0))
        day = GetDayOfYear(utc_datetime)
        declination_rad = math.radians(GetDeclination(day))
        latitude_rad = math.radians(latitude_deg)
        hour_angle_rad = math.radians(GetHourAngle(utc_datetime, longitude_deg))
        altitude_rad = math.radians(GetAltitude(latitude_deg, longitude_deg, utc_datetime))

        azimuth_rad = math.asin(math.cos(declination_rad) * math.sin(hour_angle_rad) / math.cos(altitude_rad))

        if(math.cos(hour_angle_rad) >= (math.tan(declination_rad) / math.tan(latitude_rad))):
                return math.degrees(azimuth_rad)
        else:
                return (180 - math.degrees(azimuth_rad))

def GetCoefficient(jme, constant_array):
        return sum([constant_array[i-1][0] * math.cos(constant_array[i-1][1] + (constant_array[i-1][2] * jme)) for i in range(len(constant_array))])

def GetDayOfYear(utc_datetime):
        year_start = datetime.datetime(utc_datetime.year, 1, 1, tzinfo=utc_datetime.tzinfo)
        delta = (utc_datetime - year_start)
        return delta.days

def GetDeclination(day):
        '''The declination of the sun is the angle between
        Earth's equatorial plane and a line between the Earth and the sun.
        The declination of the sun varies between 23.45 degrees and -23.45 degrees,
        hitting zero on the equinoxes and peaking on the solstices.
        '''
        return 23.45 * math.sin((2 * math.pi / 365.0) * (day - 81))

def GetEquatorialHorizontalParallax(radius_vector):
        return 8.794 / (3600 / radius_vector)

def GetFlattenedLatitude(latitude):
        latitude_rad = math.radians(latitude)
        return math.degrees(math.atan(0.99664719 * math.tan(latitude_rad)))

# Geocentric functions calculate angles relative to the center of the earth.

def GetGeocentricLatitude(jme):
        return -1 * GetHeliocentricLatitude(jme)

def GetGeocentricLongitude(jme):
        return (GetHeliocentricLongitude(jme) + 180) % 360

def GetGeocentricSunDeclination(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude):
        apparent_sun_longitude_rad = math.radians(apparent_sun_longitude)
        true_ecliptic_obliquity_rad = math.radians(true_ecliptic_obliquity)
        geocentric_latitude_rad = math.radians(geocentric_latitude)

        a = math.sin(geocentric_latitude_rad) * math.cos(true_ecliptic_obliquity_rad)
        b = math.cos(geocentric_latitude_rad) * math.sin(true_ecliptic_obliquity_rad) * math.sin(apparent_sun_longitude_rad)
        delta = math.asin(a + b)
        return math.degrees(delta)

def GetGeocentricSunRightAscension(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude):
        apparent_sun_longitude_rad = math.radians(apparent_sun_longitude)
        true_ecliptic_obliquity_rad = math.radians(true_ecliptic_obliquity)
        geocentric_latitude_rad = math.radians(geocentric_latitude)

        a = math.sin(apparent_sun_longitude_rad) * math.cos(true_ecliptic_obliquity_rad)
        b = math.tan(geocentric_latitude_rad) * math.sin(true_ecliptic_obliquity_rad)
        c = math.cos(apparent_sun_longitude_rad)
        alpha = math.atan2((a - b),  c)
        return math.degrees(alpha) % 360

# Heliocentric functions calculate angles relative to the center of the sun.

def GetHeliocentricLatitude(jme):
        b0 = GetCoefficient(jme, B0)
        b1 = GetCoefficient(jme, B1)
        return math.degrees((b0 + (b1 * jme)) / 10 ** 8)

def GetHeliocentricLongitude(jme):
        l0 = GetCoefficient(jme, L0)
        l1 = GetCoefficient(jme, L1)
        l2 = GetCoefficient(jme, L2)
        l3 = GetCoefficient(jme, L3)
        l4 = GetCoefficient(jme, L4)
        l5 = GetCoefficient(jme, L5)

        l = (l0 + l1 * jme + l2 * jme ** 2 + l3 * jme ** 3 + l4 * jme ** 4 + l5 * jme ** 5) / 10 ** 8
        return math.degrees(l) % 360

def GetHourAngle(utc_datetime, longitude_deg):
        solar_time = GetSolarTime(longitude_deg, utc_datetime)
        return 15 * (12 - solar_time)

def GetIncidenceAngle(topocentric_zenith_angle, slope, slope_orientation, topocentric_azimuth_angle):
        tza_rad = math.radians(topocentric_zenith_angle)
        slope_rad = math.radians(slope)
        so_rad = math.radians(slope_orientation)
        taa_rad = math.radians(topocentric_azimuth_angle)
        return math.degrees(math.acos(math.cos(tza_rad) * math.cos(slope_rad) + math.sin(slope_rad) * math.sin(tza_rad) * math.cos(taa_rad - math.pi - so_rad)))

def GetLocalHourAngle(apparent_sidereal_time, longitude, geocentric_sun_right_ascension):
        return (apparent_sidereal_time + longitude - geocentric_sun_right_ascension) % 360

def GetMeanSiderealTime(julian_day):
        # This function doesn't agree with Andreas and Reda as well as it should. Works to ~5 sig figs in current unit test
        jc = GetJulianCentury(julian_day)
        sidereal_time =  280.46061837 + (360.98564736629 * (julian_day - 2451545.0)) + (0.000387933 * jc ** 2) - (jc ** 3 / 38710000)
        return sidereal_time % 360

def GetNutationAberrationXY(jce, i, x):
        y = aberration_sin_terms
        sigmaxy = 0.0
        for j in range(len(x)):
                sigmaxy += x[j] * y[i][j]
        return sigmaxy

def GetNutation(jde):
        abcd = nutation_coefficients
        jce = GetJulianEphemerisCentury(jde)
        nutation_long = []
        nutation_oblique = []
        x = PrecalculateAberrations(buildPolyDict(), jce)

        for i in range(len(abcd)):
                sigmaxy = GetNutationAberrationXY(jce, i, x)
                nutation_long.append((abcd[i][0] + (abcd[i][1] * jce)) * math.sin(math.radians(sigmaxy)))
                nutation_oblique.append((abcd[i][2] + (abcd[i][3] * jce)) * math.cos(math.radians(sigmaxy)))

        # 36000000 scales from 0.0001 arcseconds to degrees
        nutation = {'longitude' : sum(nutation_long)/36000000.0, 'obliquity' : sum(nutation_oblique)/36000000.0}

        return nutation

def GetParallaxSunRightAscension(projected_radial_distance, equatorial_horizontal_parallax, local_hour_angle, geocentric_sun_declination):
        prd = projected_radial_distance
        ehp_rad = math.radians(equatorial_horizontal_parallax)
        lha_rad = math.radians(local_hour_angle)
        gsd_rad = math.radians(geocentric_sun_declination)
        a = -1 * prd * math.sin(ehp_rad) * math.sin(lha_rad)
        b =  math.cos(gsd_rad) - prd * math.sin(ehp_rad) * math.cos(lha_rad)
        parallax = math.atan2(a, b)
        return math.degrees(parallax)

def GetProjectedRadialDistance(elevation, latitude):
        flattened_latitude_rad = math.radians(GetFlattenedLatitude(latitude))
        latitude_rad = math.radians(latitude)
        return math.cos(flattened_latitude_rad) + (elevation * math.cos(latitude_rad) / earth_radius)

def GetProjectedAxialDistance(elevation, latitude):
        flattened_latitude_rad = math.radians(GetFlattenedLatitude(latitude))
        latitude_rad = math.radians(latitude)
        return 0.99664719 * math.sin(flattened_latitude_rad) + (elevation * math.sin(latitude_rad) / earth_radius)

def GetRadiusVector(jme):
        r0 = GetCoefficient(jme, R0)
        r1 = GetCoefficient(jme, R1)
        r2 = GetCoefficient(jme, R2)
        r3 = GetCoefficient(jme, R3)
        r4 = GetCoefficient(jme, R4)

        return (r0 + r1 * jme + r2 * jme ** 2 + r3 * jme ** 3 + r4 * jme ** 4) / 10 ** 8

def GetRefractionCorrection(pressure_millibars, temperature_celsius, topocentric_elevation_angle):
        tea = topocentric_elevation_angle
        temperature_kelvin = temperature_celsius + 273.15
        a = pressure_millibars * 283.0 * 1.02
        b = 1010.0 * temperature_kelvin * 60.0 * math.tan(math.radians(tea + (10.3/(tea + 5.11))))
        return a / b

def GetSolarTime(longitude_deg, utc_datetime):
        day = GetDayOfYear(utc_datetime)
        return (((utc_datetime.hour * 60) + utc_datetime.minute + (4 * longitude_deg) + EquationOfTime(day))/60)

# Topocentric functions calculate angles relative to a location on the surface of the earth.

def GetTopocentricAzimuthAngle(topocentric_local_hour_angle, latitude, topocentric_sun_declination):
        """Measured eastward from north"""
        tlha_rad = math.radians(topocentric_local_hour_angle)
        latitude_rad = math.radians(latitude)
        tsd_rad = math.radians(topocentric_sun_declination)
        a = math.sin(tlha_rad)
        b = math.cos(tlha_rad) * math.sin(latitude_rad) - math.tan(tsd_rad) * math.cos(latitude_rad)
        return 180.0 + math.degrees(math.atan2(a, b)) % 360

def GetTopocentricElevationAngle(latitude, topocentric_sun_declination, topocentric_local_hour_angle):
        latitude_rad = math.radians(latitude)
        tsd_rad = math.radians(topocentric_sun_declination)
        tlha_rad = math.radians(topocentric_local_hour_angle)
        return math.degrees(math.asin((math.sin(latitude_rad) * math.sin(tsd_rad)) + math.cos(latitude_rad) * math.cos(tsd_rad) * math.cos(tlha_rad)))

def GetTopocentricLocalHourAngle(local_hour_angle, parallax_sun_right_ascension):
        return local_hour_angle - parallax_sun_right_ascension

def GetTopocentricSunDeclination(geocentric_sun_declination, projected_axial_distance, equatorial_horizontal_parallax, parallax_sun_right_ascension, local_hour_angle):
        gsd_rad = math.radians(geocentric_sun_declination)
        pad = projected_axial_distance
        ehp_rad = math.radians(equatorial_horizontal_parallax)
        psra_rad = math.radians(parallax_sun_right_ascension)
        lha_rad = math.radians(local_hour_angle)
        a = (math.sin(gsd_rad) - pad * math.sin(ehp_rad)) * math.cos(psra_rad)
        b = math.cos(gsd_rad) - (pad * math.sin(ehp_rad) * math.cos(lha_rad))
        return math.degrees(math.atan2(a, b))

def GetTopocentricSunRightAscension(projected_radial_distance, equatorial_horizontal_parallax, local_hour_angle,
                                    apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude):
        gsd = GetGeocentricSunDeclination(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
        psra = GetParallaxSunRightAscension(projected_radial_distance, equatorial_horizontal_parallax, local_hour_angle, gsd)
        gsra = GetGeocentricSunRightAscension(apparent_sun_longitude, true_ecliptic_obliquity, geocentric_latitude)
        return psra + gsra

def GetTopocentricZenithAngle(latitude, topocentric_sun_declination, topocentric_local_hour_angle, pressure_millibars, temperature_celsius):
        tea = GetTopocentricElevationAngle(latitude, topocentric_sun_declination, topocentric_local_hour_angle)
        return 90 - tea - GetRefractionCorrection(pressure_millibars, temperature_celsius, tea)

def GetTrueEclipticObliquity(jme, nutation):
        u = jme/10.0
        mean_obliquity = 84381.448 - (4680.93 * u) - (1.55 * u ** 2) + (1999.25 * u ** 3) \
                - (51.38 * u ** 4) -(249.67 * u ** 5) - (39.05 * u ** 6) + (7.12 * u ** 7) \
                + (27.87 * u ** 8) + (5.79 * u ** 9) + (2.45 * u ** 10)
        return (mean_obliquity / 3600.0) + nutation['obliquity']

def PrecalculateAberrations(p, jce):
        x = []
        # order of 5 x.append lines below is important
        x.append(p['MeanElongationOfMoon'](jce))
        x.append(p['MeanAnomalyOfSun'](jce))
        x.append(p['MeanAnomalyOfMoon'](jce))
        x.append(p['ArgumentOfLatitudeOfMoon'](jce))
        x.append(p['LongitudeOfAscendingNode'](jce))
        return x

def GetJulianCentury(julian_day):
    return (julian_day - 2451545.0) / 36525.0

def GetJulianDay(utc_datetime):
    """This function is based on NREL/TP-560-34302 by Andreas and Reda

    This function does not accept years before 0 because of the bounds check
    on Python's datetime.year field.

    """
    year = utc_datetime.year
    month = utc_datetime.month
    if(month <= 2.0):        # shift to accomodate leap years?
        year = year - 1.0
        month = month + 12.0
    day = utc_datetime.day + (((utc_datetime.hour * 3600.0) + (utc_datetime.minute * 60.0) + utc_datetime.second + (utc_datetime.microsecond / 1000000.0)) / 86400.0)
    gregorian_offset = 2.0 - (year // 100.0) + ((year // 100.0) // 4.0)
    julian_day = math.floor(365.25 * (year + 4716.0)) + math.floor(30.6001 * (month + 1.0)) + day - 1524.5
    if (julian_day <= 2299160.0):
        return julian_day # before October 5, 1852
    else:
        return julian_day + gregorian_offset # after October 5, 1852

def GetJulianEphemerisCentury(julian_ephemeris_day):
    return (julian_ephemeris_day - 2451545.0) / 36525.0

def GetJulianEphemerisDay(julian_day, delta_seconds = 66.0):
    """delta_seconds is the value referred to by astronomers as Delta-T, defined as the difference between
    Dynamical Time (TD) and Universal Time (UT). In 2007, it's around 65 seconds.
    A list of values for Delta-T can be found here: ftp://maia.usno.navy.mil/ser7/deltat.data

    More details: http://en.wikipedia.org/wiki/DeltaT

    """
    return julian_day + (delta_seconds / 86400.0)

def GetJulianEphemerisMillenium(julian_ephemeris_century):
    return (julian_ephemeris_century / 10.0)

def GetAirMassRatio(altitude_deg):
    # from Masters, p. 412
    # warning: pukes on input of zero
    return (1/math.sin(math.radians(altitude_deg)))

def GetApparentExtraterrestrialFlux(day):
    # from Masters, p. 412
    return 1160 + (75 * math.sin(math.radians((360./365) * (day - 275))))

def GetOpticalDepth(day):
    # from Masters, p. 412
    return 0.174 + (0.035 * math.sin(math.radians((360./365) * (day - 100))))

def GetRadiationDirect(utc_datetime, altitude_deg):
    # from Masters, p. 412
    if(altitude_deg > 0):
            day = GetDayOfYear(utc_datetime)
            flux = GetApparentExtraterrestrialFlux(day)
            optical_depth = GetOpticalDepth(day)
            air_mass_ratio = GetAirMassRatio(altitude_deg)
            #return flux * math.exp(-1 * optical_depth * air_mass_ratio)
            return flux * math.exp(-1 * optical_depth * air_mass_ratio) * math.sin(math.radians(altitude_deg))
    else:
            return 0.0
