// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.2-01)
// ============================================================================
// part_id           : S2.2-01
// parent_bom_id     : S2.2
// subsystem         : S2
// part_name         : MEMS elektrostatik blanker plakasi (Arch-B es-adimli 0.50 mm, 1024 kanal)
// material          : Si
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.2 um elektrot araligi
// computed_mass_kg  : 0.00569
// envelope_mm       : 59.088 x 60.000 x 1.400
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
bbox_z = 1.4000;

// Part-specific parametric dimensions
nx = 32;
ny = 32;
pitch_mm = 0.5;
hole_d_mm = 0.26;
v_blank_V = 27.0;
f1_MHz = 2.591;

// Interface / port parameters (mm)
port_blanker_inlet_od = 60.000;
port_blanker_inlet_bore = 22.627;
port_blanker_outlet_od = 60.000;
port_blanker_outlet_bore = 22.627;

module part_S2_2_01() {
  difference() {
    union() {
      // Doped-Si 1024-ch electrostatic blanker wafer
      cylinder(d=52.000, h=0.800, center=true);
      // Stiffening perimeter bezel (f1=2.59 MHz)
      difference() {
        cylinder(d=60.000, h=1.400, center=true);
        cylinder(d=52.400, h=3.400, center=true);
      }
    }
    // 32x32 = 1,024 blanker channels
    for (ix = [0 : 32 - 1])
      for (iy = [0 : 32 - 1])
        translate([(ix - 15.500) * 0.5000, (iy - 15.500) * 0.5000, 0])
          cylinder(d=0.2600, h=1.200, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 5.160]) rotate([0.000, 0.000, 0.000]) part_S2_2_01();

part_S2_2_01();
