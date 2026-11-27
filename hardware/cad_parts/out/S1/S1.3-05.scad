// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.3-05)
// ============================================================================
// part_id           : S1.3-05
// parent_bom_id     : S1.3
// subsystem         : S1
// part_name         : Diferansiyel pompalama apertur diyaframi ve kucuk CF63 ara-oda
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.05 mm delik
// computed_mass_kg  : 2.19465
// envelope_mm       : 226.250 x 113.500 x 180.250
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 226.2500;
bbox_y = 113.5000;
bbox_z = 180.2500;

// Part-specific parametric dimensions
chamber_od = 86.0;
diaph_bore = 2.0;
diaph_axis = "Z";
diaph_z_mm = 370.66;
pump_duct_unchoked = true;
c_orifice_ph3_Ls = 0.339;
c_pump_duct_ph3_Ls = 142.0;
pressure_ratio = 418.9;

// Interface / port parameters (mm)
port_diff_pump_cf63_neg_x_od = 113.500;
port_diff_pump_cf63_neg_x_bore = 63.500;
port_diff_pump_cf63_neg_x_pcd = 92.100;
port_diff_pump_cf63_neg_x_bolts = 8;
port_source_mate_cf40_pos_x_od = 69.500;
port_source_mate_cf40_pos_x_bore = 38.000;
port_source_mate_cf40_pos_x_pcd = 58.700;
port_source_mate_cf40_pos_x_bolts = 6;
port_inline_beam_orifice_z_od = 83.000;
port_inline_beam_orifice_z_bore = 2.000;
port_gauge_port_cf16_top_od = 33.800;
port_gauge_port_cf16_top_bore = 16.000;
port_gauge_port_cf16_top_pcd = 27.000;
port_gauge_port_cf16_top_bolts = 6;

module part_S1_3_05() {
  union() {
    // Unchoked 316LN CF63 differential pump chamber
    translate([2.000, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=86.000, h=94.000, center=true);
        cylinder(d=76.000, h=96.000, center=true);
      }
    }
    // ISO 3669 CF63 differential pump flange
    translate([-55.000, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        cylinder(d=63.500, h=19.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // ISO 3669 CF40 source-side flange
    translate([56.350, 0.000, 0.000]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=38.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
    // Inline Z-axis Mo Ø2.0 mm differential pumping diaphragm
    translate([121.000, 0.000, -122.000]) {
      difference() {
        cylinder(d=83.000, h=3.000, center=true);
        cylinder(d=2.000, h=5.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-121.000, 0.000, 492.660]) rotate([0.000, 0.000, 0.000]) part_S1_3_05();

part_S1_3_05();
