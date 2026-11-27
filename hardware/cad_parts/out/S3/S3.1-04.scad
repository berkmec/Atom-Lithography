// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S3.1-04)
// ============================================================================
// part_id           : S3.1-04
// parent_bom_id     : S3.1
// subsystem         : S3
// part_name         : Altin kapli yayli IBIC yonga temas halkasi (cantilever contact ring)
// material          : BeCu
// temp_stage        : 4 K - 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±10 um konum
// computed_mass_kg  : 0.03069
// envelope_mm       : 81.995 x 81.892 x 2.430
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 81.9949;
bbox_y = 81.8919;
bbox_z = 2.4300;

// Part-specific parametric dimensions
ring_id_mm = 64.0;
shield_od_mm = 82.0;
n_spring_fingers = 16;
bolt_pcd_mm = 71.2;

// Interface / port parameters (mm)
port_cantilever_contacts_od = 64.000;
port_cantilever_contacts_bore = 57.600;
port_coax_terminal_ring_od = 82.000;
port_mount_bolts_pcd = 71.200;
port_mount_bolts_bolts = 6;

module part_S3_1_04() {
  difference() {
    union() {
      // BeCu/Au cantilever spring base ring (Ø64/Ø78.4)
      translate([0.000, 0.000, 0.100]) {
        difference() {
          cylinder(d=78.400, h=1.800, center=true);
          cylinder(d=64.000, h=3.800, center=true);
        }
      }
      // Integrated outer Faraday bias shield shroud
      translate([0.000, 0.000, 0.200]) {
        difference() {
          cylinder(d=82.000, h=2.400, center=true);
          cylinder(d=78.700, h=4.400, center=true);
        }
      }
    }
    // 6x M2.5 mounting bolt circle
    translate([0.000, 0.000, 0.100]) {
      for (i = [0 : 6 - 1])
        rotate([0, 0, i * 360 / 6])
          translate([35.600, 0, 0])
            cylinder(d=2.700, h=4.000, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 1.000]) rotate([0.000, 0.000, 0.000]) part_S3_1_04();

part_S3_1_04();
