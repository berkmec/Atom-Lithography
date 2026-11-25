// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.5-01)
// ============================================================================
// part_id           : S1.5-01
// parent_bom_id     : S1.5
// subsystem         : S1
// part_name         : Yari-kuresel HDA-HiRes enerji suzgeci (R0=40 mm, dE=0.453 eV, Exp124)
// material          : Ti-6Al-4V
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±5 um kure profili
// computed_mass_kg  : 0.89953
// envelope_mm       : 110.000 x 110.000 x 95.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 110.0000;
bbox_y = 110.0000;
bbox_z = 95.0000;

// Part-specific parametric dimensions
r0_mm = 40.0;
r_inner_mm = 36.0;
r_outer_mm = 44.0;
e_pass_eV = 100.0;
dE_fwhm_eV = 0.453;

// Interface / port parameters (mm)
port_hda_inlet_top_od = 110.000;
port_hda_inlet_top_bore = 16.000;
port_hda_inlet_top_pcd = 106.000;
port_hda_inlet_top_bolts = 16;
port_hda_outlet_bot_od = 110.000;
port_hda_outlet_bot_bore = 16.000;
port_hda_outlet_bot_pcd = 106.000;
port_hda_outlet_bot_bolts = 16;

module part_S1_5_01() {
  difference() {
    union() {
      // Ti-6Al-4V UHV HDA outer housing
      difference() {
        cylinder(d=110.000, h=95.000, center=true);
        cylinder(d=102.000, h=97.000, center=true);
      }
      // Equatorial Au-OFHC Jost baseplate
      translate([-7.500, 0.000, 0.000]) cube([4.000, 88.000, 88.000], center=true);
      // Jost entrance deceleration lens
      translate([-24.000, 0.000, 40.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=11.600, h=28.000, center=true);
      // Jost exit acceleration lens
      translate([-24.000, 0.000, -40.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=11.600, h=28.000, center=true);
    }
    // 16xM3 housing end-ring bolts
    for (i = [0 : 16 - 1])
      rotate([0, 0, i * 360 / 16])
        translate([53.000, 0, 0])
          cylinder(d=3.200, h=98.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 162.160]) rotate([0.000, 0.000, 0.000]) part_S1_5_01();

part_S1_5_01();
