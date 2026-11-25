// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.SAFETY-01)
// ============================================================================
// part_id           : S7.SAFETY-01
// parent_bom_id     : S7.SAFETY
// subsystem         : S7
// part_name         : Sub-Atmosferik SDS PH3 Mikro-Tup Gaz Kabini (<650 Torr, 10 g), Vakum-Ceketli Hat, 250 CFM Kuru Yikayici & Cift 0.02 ppm Sensor (Exp150, 118.0 kg)
// material          : 316L
// temp_stage        : 300 K (tesis gaz bolmesi)
// vacuum_grade      : Atmosfer (250 CFM egzoz)
// tolerance         : PH3<=0.02 ppm alarm (SIL-3)
// computed_mass_kg  : 118.00000
// envelope_mm       : 875.000 x 655.500 x 2060.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 875.0000;
bbox_y = 655.5000;
bbox_z = 2060.0000;

// Part-specific parametric dimensions
cab_dx_mm = 500.0;
cab_dy_mm = 600.0;
cab_dz_mm = 1800.0;
scrubber_od_mm = 320.0;
exhaust_cfm = 250;

// Interface / port parameters (mm)
port_ph3_vcr_outlet_od = 19.000;
port_ph3_vcr_outlet_bore = 4.500;
port_exhaust_250cfm_dn100_od = 114.000;
port_exhaust_250cfm_dn100_bore = 100.000;

module part_S7_SAFETY_01() {
  difference() {
    union() {
      // SEMI S2 target SDS PH3 gas cabinet
      cube([500.000, 600.000, 1800.000], center=true);
      // 250 CFM dry-bed chemical scrubber
      translate([-460.000, 0.000, -540.000]) cylinder(d=320.000, h=720.000, center=true);
      // DN100 vacuum-jacketed exhaust riser
      translate([0.000, 0.000, 975.000]) {
        difference() {
          cylinder(d=108.000, h=150.000, center=true);
          cylinder(d=80.000, h=152.000, center=true);
        }
      }
    }
    // Armored front inspection window
    translate([0.000, -295.000, 260.000]) rotate([90.000, 90.000, 0.000]) {
      hull() {
        translate([-110.000, 0, 0]) cylinder(d=260.000, h=40.000, center=true);
        translate([110.000, 0, 0]) cylinder(d=260.000, h=40.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-1600.000, 400.000, 900.000]) rotate([0.000, 0.000, 0.000]) part_S7_SAFETY_01();

part_S7_SAFETY_01();
