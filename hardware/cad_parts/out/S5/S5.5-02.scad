// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.5-02)
// ============================================================================
// part_id           : S5.5-02
// parent_bom_id     : S5.5
// subsystem         : S5
// part_name         : CF63 +Y ekvatoral (Z=500 mm) AR-kapli safir vakum penceresi ve optik flans (Exp130)
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : lambda/10, He<=1e-10
// computed_mass_kg  : 1.10806
// envelope_mm       : 113.500 x 17.500 x 113.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 113.5000;
bbox_y = 17.5000;
bbox_z = 113.5000;

// Part-specific parametric dimensions
cf63_od = 113.5;
clear_aperture_mm = 44.0;
sapphire_d = 50.0;
sapphire_t = 8.0;

// Interface / port parameters (mm)
port_chamber_pos_y_cf63_od = 113.500;
port_chamber_pos_y_cf63_bore = 44.000;
port_chamber_pos_y_cf63_pcd = 92.100;
port_chamber_pos_y_cf63_bolts = 8;
port_optical_808nm_in_od = 50.000;
port_optical_808nm_in_bore = 44.000;

module part_S5_5_02() {
  union() {
    // ISO 3669 CF63 316LN optical viewport flange (8xM8 @ PCD 92.1)
    translate([0.000, 8.750, 0.000]) rotate([90.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        cylinder(d=44.000, h=19.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // Single-crystal AR sapphire window (Dia 50x8 mm, Dia 44 mm CA)
    translate([0.000, 13.500, 0.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=50.000, h=8.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 295.500, 500.000]) rotate([0.000, 0.000, 0.000]) part_S5_5_02();

part_S5_5_02();
