import math
import re

PRINT_SPEED = 30000;
EXTRUDER_SPEED = 0.2;
Z_POS = 35.0;
SKIA_XY_RANGE = 330;
PRINTER_XY_RANGE = 220;

GCODE_CONST = {
    "start": "M104 S32\n M109 S32\n M302 P1\n M203 E999\n G28\n G92 E0\n G1 Z35.0 F30000\n",
    "end": "\n G91\n G1 Y100 E65\n G90\n G1 X0 Y200 Z50 \n"
}

def convertToGcode(paths, extruderSpeed=EXTRUDER_SPEED, zPos=Z_POS,
    xyRange=SKIA_XY_RANGE, printerRange=PRINTER_XY_RANGE):
    result = GCODE_CONST['start']
    scale = printerRange / xyRange;
    extruderPosition = 0

    for path in paths:
        print('path: ', path)
        # Split the path into coordinates
        data = re.split(r'[ML]', path)
        filtered = list(filter(lambda x: x != '', data))
        prevData = ''
        final = []
        for line in filtered:
            if line != prevData:
                final.append(line)
            prevData = line
        print(filtered, '\n', final)
        #filtered = list(dict.fromkeys(filtered))

        # For each coord pass a line directing the printer to the next destination
        for s in final:
            data = s.split(' ')
            if path == paths[0] and s == final[0]:
                result += f'\n G1 X{(float(data[0])*scale*0.5)+75} Y{((xyRange - float(data[1])) * scale * 0.5) + 75} Z{zPos} E-110 \n G92 E20';
            elif s == final[0]:
                result += f'\n G1 X{(float(data[0])*scale*0.5)+75} Y{((xyRange - float(data[1])) * scale * 0.5) + 75} E{extruderPosition + 65}';
                #extruderPosition += 15;
            else:
                index = filtered.index(s)
                length = 1
                dExtrude = 0
                if index > 1:
                    prev = filtered[index - 1].split(' ')
                    xDiff = float(prev[0]) - float(data[0])
                    yDiff = float(prev[1]) - float(data[1])
                    length = math.sqrt(math.pow(xDiff*scale, 2) + math.pow(yDiff*scale, 2))
                    dExtrude = length * extruderSpeed;

                result += f'\n G1 F{PRINT_SPEED / length} X{(float(data[0])*scale*0.5)+75} Y{((xyRange - float(data[1])) * scale * 0.5) + 75} E{extruderPosition - dExtrude}';
                extruderPosition -= dExtrude;

    result += GCODE_CONST['end']
    return result
