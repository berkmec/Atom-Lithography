// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.3-02)
// ============================================================================
// part_id           : S1.3-02
// parent_bom_id     : S1.3
// subsystem         : S1
// part_name         : 10->5 keV elektrostatik yavaslatma daldirma lensi (Exp124 Arch-B delta)
// material          : Ti-6Al-4V
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±2 um es-merkezlilik
// computed_mass_kg  : 1.00327
// envelope_mm       : 84.000 x 84.000 x 65.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 84.0000;
bbox_y = 84.0000;
bbox_z = 65.0000;

// Part-specific parametric dimensions
od = 84.0;
bore = 28.0;
height = 65.0;
e_land_keV = 5.0;

// Interface / port parameters (mm)
port_decel_outlet_to_s2_od = 84.000;
port_decel_outlet_to_s2_bore = 28.000;
port_decel_outlet_to_s2_pcd = 77.000;
port_decel_outlet_to_s2_bolts = 12;
port_transfer_inlet_from_hda_od = 84.000;
port_transfer_inlet_from_hda_bore = 28.000;
port_transfer_inlet_from_hda_pcd = 77.000;
port_transfer_inlet_from_hda_bolts = 12;

module part_S1_3_02() {
  difference() {
    union() {
      // Ti-6Al-4V precision outer optical barrel
      difference() {
        cylinder(d=84.000, h=65.000, center=true);
        cylinder(d=70.000, h=67.000, center=true);
      }
      // Lower Mo decel electrode
      translate([0.000, 0.000, -23.660]) {
        difference() {
          cylinder(d=64.000, h=15.000, center=true);
          cylinder(d=28.000, h=17.000, center=true);
        }
      }
      // Middle Einzel focus electrode
      difference() {
        cylinder(d=64.000, h=20.000, center=true);
        cylinder(d=28.000, h=22.000, center=true);
      }
      // Upper Mo transfer electrode
      translate([0.000, 0.000, 23.340]) {
        difference() {
          cylinder(d=64.000, h=15.000, center=true);
          cylinder(d=28.000, h=17.000, center=true);
        }
      }
    }
    // 12xM4 optical barrel mounting circle
    for (i = [0 : 12 - 1])
      rotate([0, 0, i * 360 / 12])
        translate([38.500, 0, 0])
          cylinder(d=4.300, h=68.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 72.160]) rotate([0.000, 0.000, 0.000]) part_S1_3_02();

part_S1_3_02();
