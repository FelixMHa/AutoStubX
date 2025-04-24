

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Short.hashCode(input_1_0);
        Integer output_2 = Short.hashCode(input_2_0);

        
        // Compare output
        if (output_1 == 32767 && output_2 == 0) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

