

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Long.numberOfLeadingZeros(input_1_0);
        Integer output_2 = Long.numberOfLeadingZeros(input_2_0);

        
        // Compare output
        if (output_1 == 25 && output_2 == 63) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

