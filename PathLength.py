import FreeCAD
import Path
import PathScripts.PathGeom as PathGeom

class PathLength(object):

    def __init__(self, path):
        self.path = path
        self.length = []

        last = FreeCAD.Vector(0, 0, 0)
        total = 0
        for cmd in path.Commands:
            x = cmd.Parameters.get('X', last.x)
            y = cmd.Parameters.get('Y', last.y)
            z = cmd.Parameters.get('Z', last.z)
            end = FreeCAD.Vector(x, y, z)
            if cmd.Name in ['G0', 'G00', 'G1', 'G01']:
                total += end.distanceToPoint(last)
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
                total += angle * radius
            last = end
            self.length.append(total)
        self.total = total

    def totalLength(self):
        '''Return the overall length of the Path.'''
        return self.total

    def percentDone(self, lineNr, distanceToGo):
        '''percentDone(lineNr, distanceToGo) ... Return a float 0-1.0 of where the given lineNr is in relation to the overall length.'''
        if lineNr >= len(self.length):
            #print("percentDone(%d/%d) = 1" % (lineNr, len(self.length)))
            return 1
        done = (self.length[lineNr] - distanceToGo) / self.total
        #print("percentDone(%d/%d) = %.2f" % (lineNr, len(self.length), done))
        return done

def From(path):
    '''Return a PathLength object for the given Path'''
    return PathLength(path)

def FromGCode(gcode):
    '''Return a PathLength object for the given gcode'''
    return From(Path.Path([Path.Command(line.upper()) for line in gcode]))
