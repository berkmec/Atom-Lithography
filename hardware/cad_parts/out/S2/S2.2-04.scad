// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.2-04)
// ============================================================================
// part_id           : S2.2-04
// parent_bom_id     : S2.2
// subsystem         : S2
// part_name         : Saptirilmis iyon durdurma diyaframi (beam-stop Faraday plakasi)
// material          : Mo
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±20 um aciklik
// computed_mass_kg  : 0.01813
// envelope_mm       : 59.088 x 60.000 x 1.200
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 59.0885;
bbox_y = 60.0000;
bbox_z = 1.2000;

// Part-specific parametric dimensions
nx = 32;
ny = 32;
pitch_mm = 0.5;
stop_hole_mm = 0.012;
blanked_leak_frac = 0.0;
backscatter_max = 0.0001;

// Interface / port parameters (mm)
port_beamstop_inlet_od = 60.000;
port_beamstop_inlet_bore = 22.627;
port_beamstop_outlet_od = 60.000;
port_beamstop_outlet_bore = 22.627;

module part_S2_2_04() {
  difference() {
    union() {
      // Graphite-coated Mo beam-stop diaphragm
      cylinder(d=50.000, h=0.500, center=true);
      // OFHC Cu thermal sink mounting rim
      difference() {
        cylinder(d=60.000, h=1.200, center=true);
        cylinder(d=52.400, h=3.200, center=true);
      }
    }
    // 32x32 Ø12.0 um pass-through beam-stop apertures
    for (ix = [0 : 32 - 1])
      for (iy = [0 : 32 - 1])
        translate([(ix - 15.500) * 0.5000, (iy - 15.500) * 0.5000, 0])
          cylinder(d=0.0120, h=1.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 3.610]) rotate([0.000, 0.000, 0.000]) part_S2_2_04();

part_S2_2_04();
