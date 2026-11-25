// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.3-03)
// ============================================================================
// part_id           : S6.3-03
// parent_bom_id     : S6.3
// subsystem         : S6
// part_name         : Cift-katmanli Nb (RRR>300) + Cryoperm-10 Meissner kalkan kabı (Exp125 delta)
// material          : Nb
// temp_stage        : 4 K / 20 mK
// vacuum_grade      : Kriyo-vakum
// tolerance         : ±0.1 mm
// computed_mass_kg  : 0.64382
// envelope_mm       : 82.000 x 82.000 x 58.600
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 82.0000;
bbox_y = 82.0000;
bbox_z = 58.6000;

// Part-specific parametric dimensions
nb_r_in = 32.0;
nb_r_out = 34.5;
cp_r_in = 39.0;
cp_r_out = 41.0;
n_vents = 6;

// Interface / port parameters (mm)
port_chimney_coax_port_od = 16.000;
port_chimney_coax_port_bore = 12.000;
port_resonator_cavity_od = 69.000;
port_resonator_cavity_bore = 64.000;
port_cryoperm_vent_base_od = 82.000;
port_cryoperm_vent_base_bore = 28.000;
port_cryoperm_vent_base_pcd = 54.000;
port_cryoperm_vent_base_bolts = 6;

module part_S6_3_03() {
  difference() {
    union() {
      // Nb RRR>300 Meissner cup
      translate([0.000, 0.000, -1.250]) {
        difference() {
          cylinder(d=69.000, h=35.500, center=true);
          cylinder(d=64.000, h=37.500, center=true);
        }
      }
      // Nb attenuating chimney
      translate([0.000, 0.000, 24.650]) {
        difference() {
          cylinder(d=16.000, h=10.900, center=true);
          cylinder(d=12.000, h=12.900, center=true);
        }
      }
      // Cryoperm-10 outer shield
      translate([0.000, 0.000, 3.000]) {
        difference() {
          cylinder(d=82.000, h=56.000, center=true);
          cylinder(d=78.000, h=58.000, center=true);
        }
      }
    }
    // 6x M2.5 lid bolt circle
    translate([0.000, 0.000, 17.850]) {
      for (i = [0 : 6 - 1])
        rotate([0, 0, i * 360 / 6])
          translate([30.000, 0, 0])
            cylinder(d=2.700, h=4.000, center=true);
    }
    // 6x Ø3.5 mm vacuum vent holes
    translate([0.000, 0.000, -26.350]) {
      for (i = [0 : 6 - 1])
        rotate([0, 0, i * 360 / 6])
          translate([27.000, 0, 0])
            cylinder(d=3.500, h=4.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 345.000]) rotate([0.000, 0.000, 0.000]) part_S6_3_03();

part_S6_3_03();
