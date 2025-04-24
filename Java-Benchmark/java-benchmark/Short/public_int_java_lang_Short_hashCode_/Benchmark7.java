

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Short input_1_0 = Short.valueOf(args[0]);
        Short input_2_0 = Short.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = input_1_0.hashCode();
        Integer output_2 = input_2_0.hashCode();

        
        // Compare output
        if (output_1 == -4756 && output_2 == -4905) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

