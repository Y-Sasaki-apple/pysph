"""Simple Inlet and Outlet support for PySPH.  The inlet and outlets are axis
aligned.

The Inlet lets a user stack a given set of inlet particles along a particular
coordinate axis.  As the particles move they are copied over to a specified
destination particle array.  The particles are also wrapped back into the
inlet.

The Outlet lets a user specify a region where any particles enter will be
added to a specified "outlet" particle array and removed from the source
array.  When outlet particles leave the outlet region (specified with a
bounding box) they are removed from the simulation.

Copyright (c) 2015, Prabhu Ramachandran
License: BSD
"""

import numpy as np


class SimpleInlet(object):

    """This inlet has particles stacked along a particular axis (defaults to
    'x').  These particles can move along any direction and as they flow out
    of the domain they are copied into the destination particle array at each
    timestep.

    Inlet particles are stacked by subtracting the spacing amount from the
    existing inlet array. These are copied when the inlet is created.  The
    particles that cross the inlet domain are copied over to the destination
    particle array and moved back to the other side of the inlet.

    The motion of the particles can be along any direction required.  One
    can set the 'u' velocity to have a parabolic profile in the 'y' direction
    if so desired.

    """
    def __init__(self, inlet_pa, dest_pa, spacing, n=5, axis='x',
                 xmin=-1.0, xmax=1.0, ymin=-1.0, ymax=1.0, zmin=-1.0, zmax=1.0):
        """Constructor.

        Arguments
        -----------

         inlet_pa - Particle array for the inlet particles.

         dest_pa - Particle array for the destination into which inlet flows.

         spacing - Spacing of particles in the inlet domain.

         n - Total number of copies of the initial particles.

         axis: one of 'x', 'y', 'z' - Axis along which to stack particles.

         xmin, xmax, ymin, ymax, zmin, zmax - Domain of the outlet.

        """
        self.inlet_pa = inlet_pa
        self.dest_pa = dest_pa
        self.spacing = spacing
        assert axis in ('x', 'y', 'z')
        self.axis = axis
        self.n = n
        self.xmin, self.xmax = xmin, xmax
        self.ymin, self.ymax = ymin, ymax
        self.zmin, self.zmax = zmin, zmax
        self._create_inlet_particles()

    def _create_inlet_particles(self):
        props =  self.inlet_pa.get_property_arrays()
        inlet_props = {}
        for prop, array in props.iteritems():
            new_array = np.array([], dtype=array.dtype)
            for i in range(1, self.n):
                if prop == self.axis:
                    new_array = np.append(new_array, array - i*self.spacing)
                else:
                    new_array = np.append(new_array, array)
            inlet_props[prop] = new_array
        self.inlet_pa.add_particles(**inlet_props)

    def update(self, solver=None):
        """This is called by the solver after each timestep and is passed
        the solver instance.
        """
        pa_add = {}
        inlet_pa = self.inlet_pa
        xmin, xmax, ymin, ymax = self.xmin, self.xmax, self.ymin, self.ymax
        zmin, zmax = self.zmin, self.zmax
        lx, ly, lz = xmax - xmin, ymax - ymin, zmax - zmin
        x, y, z = inlet_pa.x, inlet_pa.y, inlet_pa.z

        xcond = (x > xmax) | (x < xmin)
        ycond = (y > ymax) | (y < ymin)
        zcond = (z > zmax) | (z < zmin)
        # All the indices of particles which have left.
        all_idx = np.where(xcond | ycond | zcond)[0]
        # The indices which need to be wrapped around.
        x_idx = np.where(xcond)[0]
        y_idx = np.where(ycond)[0]
        z_idx = np.where(zcond)[0]

        # adding particles to the destination array.
        props = inlet_pa.get_property_arrays()
        for prop, array in props.iteritems():
            pa_add[prop] = np.array(array[all_idx])
        self.dest_pa.add_particles(**pa_add)

        # moving the moved particles back to the array beginning.
        inlet_pa.x[x_idx] -=  np.sign(inlet_pa.x[x_idx] - xmax)*lx
        inlet_pa.y[y_idx] -=  np.sign(inlet_pa.y[y_idx] - ymax)*ly
        inlet_pa.z[z_idx] -=  np.sign(inlet_pa.z[z_idx] - zmax)*lz


class SimpleOutlet(object):

    """This outlet simply moves the particles that comes into it from the
    source and removes any that leave the box.

    """
    def __init__(self, outlet_pa, source_pa, xmin=-1.0, xmax=1.0,
                 ymin=-1.0, ymax=1.0, zmin=-1.0, zmax=1.0):
        """Constructor.

        Arguments
        -----------

         outlet_pa - Particle array for the outlet particles.

         source_pa - Particle array from which the particles flow in.

         xmin, xmax, ymin, ymax, zmin, zmax - Domain of the outlet.

        """
        self.outlet_pa = outlet_pa
        self.source_pa = source_pa
        self.xmin, self.xmax = xmin, xmax
        self.ymin, self.ymax = ymin, ymax
        self.zmin, self.zmax = zmin, zmax

    def update(self, solver=None):
        """This is called by the solver after each timestep and is passed
        the solver instance.
        """
        xmin, xmax, ymin, ymax = self.xmin, self.xmax, self.ymin, self.ymax
        zmin, zmax = self.zmin, self.zmax
        outlet_pa = self.outlet_pa
        source_pa = self.source_pa
        x, y, z = source_pa.x, source_pa.y, source_pa.z
        idx = np.where((x <= xmax) & (x >= xmin) & (y <= ymax) & (y >= ymin) &
                       (z <= zmax) & (z >= zmin))[0]

        # adding particles to the destination array.
        pa_add = {}
        props = source_pa.get_property_arrays()
        for prop, array in props.iteritems():
            pa_add[prop] = np.array(array[idx])
        outlet_pa.add_particles(**pa_add)

        # removing the particles that moved into the outlet
        source_pa.remove_particles(idx)

        x, y, z = outlet_pa.x, outlet_pa.y, outlet_pa.z
        idx = np.where((x > xmax) | (x < xmin) | (y > ymax) | (y < ymin) |
                       (z > zmax) | (z < zmin))[0]
        outlet_pa.remove_particles(idx)
