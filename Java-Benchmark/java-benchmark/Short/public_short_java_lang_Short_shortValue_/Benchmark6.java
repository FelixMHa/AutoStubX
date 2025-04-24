

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Short output_1 = input_1_0.shortValue();
        Short output_2 = input_2_0.shortValue();

        
        // Compare output
        if (output_1 == -1918 && output_2 == -7629) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

