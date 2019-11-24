import FreeCAD
import Path
import PathScripts.PathGeom as PathGeom

class PathLength(object):

    def __init__(self, path, rapidSpeed=None):
        self.path = path
        self.length = []
        self.scaled = []
        self.scale = []
        self.dist = []

        velocity = 0
        last = FreeCAD.Vector(0, 0, 0)
        total = 0
        totalScaled = 0
        for cmd in path.Commands:
            dist = 0
            x = cmd.Parameters.get('X', last.x)
            y = cmd.Parameters.get('Y', last.y)
            z = cmd.Parameters.get('Z', last.z)
            end = FreeCAD.Vector(x, y, z)
            if cmd.Name in ['G0', 'G00', 'G1', 'G01']:
                dist = end.distanceToPoint(last)
            if cmd.Name in ['G2', 'G02', 'G3', 'G03']:
                cx = last.x + cmd.Parameters.get('I', 0)
                cy = last.y + cmd.Parameters.get('J', 0)
                cz = last.z + cmd.Parameters.get('K', 0)
                center = FreeCAD.Vector(cx, cy, cz)
                radius = center.distanceToPoint(last)
                r2 = center.distanceToPoint(end)
                if not PathGeom.isRoughly(radius, r2, 0.002):
                    print("There's something wrong with %s, %.4f vs. %.4f" % (cmd, radius, r2))
                angle = (end - center).getAngle(last - center)
                dend = end - center
                dlast = last - center
                dist = angle * radius

            total += dist
            scale = 1
            if rapidSpeed is None:
                totalScaled = total
            elif dist > 0:
                if cmd.Name in ['G0', 'G00']:
                    scale = rapidSpeed
                else:
                    velocity = cmd.Parameters.get('F', velocity)
                    scale = min(rapidSpeed, velocity / 60.0)
                totalScaled += dist / scale
            self.length.append(total)
            self.scaled.append(totalScaled)
            self.scale.append(scale)
            self.dist.append(dist)
            last = end
        self.total = total
        self.totalScaled = totalScaled

    def totalLength(self, scaled=False):
        '''Return the overall length of the Path.'''
        if scaled:
            return self.totalScaled
        return self.total

    def percentDone(self, lineNr, distanceToGo, scaled=False):
        '''percentDone(lineNr, distanceToGo, scaled=False) ... Return a float 0-1.0 of where the given lineNr is in relation to the overall length.
        If scaled=True the algorithm takes the feed rate of each move into account.'''
        if lineNr >= len(self.length):
            return 1

        if scaled:
            done = (self.scaled[lineNr] - min(distanceToGo, self.dist[lineNr]) / self.scale[lineNr]) / self.totalScaled
        else:
            done = (self.length[lineNr] - min(distanceToGo, self.dist[lineNr])) / self.total
        return done

def From(path, rapidSpeed=None):
    '''Return a PathLength object for the given Path'''
    return PathLength(path, rapidSpeed)

def FromGCode(gcode, rapidSpeed=None):
    '''Return a PathLength object for the given gcode'''
    return From(Path.Path([Path.Command(line.upper()) for line in gcode]), rapidSpeed)
