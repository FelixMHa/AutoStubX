

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Long.valueOf(input_1_0);
        Long output_2 = Long.valueOf(input_2_0);

        
        // Compare output
        if (output_1 == -9235911098820985L && output_2 == 84284L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

