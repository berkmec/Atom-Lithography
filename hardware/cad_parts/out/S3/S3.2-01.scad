// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S3.2-01)
// ============================================================================
// part_id           : S3.2-01
// parent_bom_id     : S3.2
// subsystem         : S3
// part_name         : 100 K soguk-ada 8-kanalli ultra-dusuk-C LTC6268 CSA modulleri (Exp127 kilitli)
// material          : OFHC Cu
// temp_stage        : 100 K (soguk ada)
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±5% kazanc
// computed_mass_kg  : 0.47802
// envelope_mm       : 267.700 x 269.232 x 13.982
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 267.7000;
bbox_y = 269.2316;
bbox_z = 13.9817;

// Part-specific parametric dimensions
n_csa_modules = 16;
channels_total = 128;
module_r_in_mm = 86.0;
module_r_out_mm = 118.0;
bus_r_out_mm = 142.0;
operating_temp_k = 100.0;

// Interface / port parameters (mm)
port_csa_16x_coax_in_bore = 172.000;
port_cold_island_100k_bus_od = 284.000;
port_cold_island_100k_bus_bore = 268.000;

module part_S3_2_01() {
  union() {
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #1 (22 deg)
    translate([94.573, 38.210, -0.100]) rotate([0.000, 0.000, 22.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #2 (35 deg)
    translate([83.554, 58.505, -0.100]) rotate([0.000, 0.000, 35.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #3 (58 deg)
    translate([54.052, 86.501, -0.100]) rotate([0.000, 0.000, 58.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #4 (70 deg)
    translate([34.886, 95.849, -0.100]) rotate([0.000, 0.000, 70.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #5 (114 deg)
    translate([-41.487, 93.182, -0.100]) rotate([0.000, 0.000, 114.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #6 (128 deg)
    translate([-62.797, 80.377, -0.100]) rotate([0.000, 0.000, 128.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #7 (142 deg)
    translate([-80.377, 62.797, -0.100]) rotate([0.000, 0.000, 142.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #8 (156 deg)
    translate([-93.182, 41.487, -0.100]) rotate([0.000, 0.000, 156.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #9 (204 deg)
    translate([-93.182, -41.487, -0.100]) rotate([0.000, 0.000, 204.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #10 (218 deg)
    translate([-80.377, -62.797, -0.100]) rotate([0.000, 0.000, 218.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #11 (232 deg)
    translate([-62.797, -80.377, -0.100]) rotate([0.000, 0.000, 232.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #12 (246 deg)
    translate([-41.487, -93.182, -0.100]) rotate([0.000, 0.000, 246.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #13 (294 deg)
    translate([41.487, -93.182, -0.100]) rotate([0.000, 0.000, 294.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #14 (308 deg)
    translate([62.797, -80.377, -0.100]) rotate([0.000, 0.000, 308.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #15 (322 deg)
    translate([80.377, -62.797, -0.100]) rotate([0.000, 0.000, 322.000]) cube([32.000, 14.500, 10.800], center=true);
    // 100 K Cold-Island 8-ch LTC6268 CSA Module #16 (336 deg)
    translate([93.182, -41.487, -0.100]) rotate([0.000, 0.000, 336.000]) cube([32.000, 14.500, 10.800], center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -8.500]) rotate([0.000, 0.000, 0.000]) part_S3_2_01();

part_S3_2_01();
