// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.2-01)
// ============================================================================
// part_id           : S9.2-01
// parent_bom_id     : S9.2
// subsystem         : S9
// part_name         : Yuksek saflikta PH3 (%5 H2/Ar) ve 29SiF4/28SiF4 kaynak gaz tupleri (1 yil)
// material          : 316L
// temp_stage        : 300 K (gaz kabini)
// vacuum_grade      : Basincli tup
// tolerance         : >99.999%
// computed_mass_kg  : 168.00000
// envelope_mm       : 840.000 x 320.000 x 1381.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 840.0000;
bbox_y = 320.0000;
bbox_z = 1381.5000;

// Part-specific parametric dimensions
qty_cylinders = 4;
cyl_od_mm = 164.0;
rack_w_mm = 840.0;

// Interface / port parameters (mm)

module part_S9_2_01() {
  union() {
    // Seismic floor baseplate
    translate([0.000, 0.000, -702.000]) cube([840.000, 320.000, 16.000], center=true);
    // Cylinder #1 (PH3)
    translate([-292.500, -20.000, -20.000]) cylinder(d=164.000, h=1340.000, center=true);
    // Cylinder #2 (29SiF4)
    translate([-97.500, -20.000, -20.000]) cylinder(d=164.000, h=1340.000, center=true);
    // Cylinder #3 (28SiF4)
    translate([97.500, -20.000, -20.000]) cylinder(d=164.000, h=1340.000, center=true);
    // Cylinder #4 (Ar/N2)
    translate([292.500, -20.000, -20.000]) cylinder(d=164.000, h=1340.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-1350.000, -1520.000, 710.000]) rotate([0.000, 0.000, 0.000]) part_S9_2_01();

part_S9_2_01();
